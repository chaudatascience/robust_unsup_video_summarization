import argparse, os, sys, datetime, glob

from omegaconf import OmegaConf

import pytorch_lightning as pl
from pytorch_lightning.plugins import DDPPlugin
from pytorch_lightning import seed_everything
from pytorch_lightning.trainer import Trainer
from pytorch_lightning.callbacks import ModelCheckpoint
from pytorch_lightning.loggers import WandbLogger


from lit_models.lit_aln_uni_y8 import LitModel 
from custom_callbacks import SetupCallback

def get_parser(**parser_kwargs):
    def str2bool(v):
        if isinstance(v, bool):
            return v
        if v.lower() in ("yes", "true", "t", "y", "1"):
            return True
        elif v.lower() in ("no", "false", "f", "n", "0"):
            return False
        else:
            raise argparse.ArgumentTypeError("Boolean value expected.")

    parser = argparse.ArgumentParser(**parser_kwargs)
    parser.add_argument(
        "-n",
        "--name",
        type=str,
        const=True,
        nargs="?",
        help="postfix for logdir",
    )

    parser.add_argument(
        "-b",
        "--base",
        nargs="*",
        metavar="base_config.yaml",
        help="paths to base configs. Loaded from left-to-right. "
        "Parameters can be overwritten or added with command-line options of the form `--key value`.",
        default=list(),
    )

    parser.add_argument(
        "--seed",
        type=int,
        const=True,
        default=0,
        nargs="?",
        help="random seed",
    )
    
    parser.add_argument(
        "-r",
        "--resume",
        type=bool,
        # const=False,
        nargs="?",
        default=False,
    )
    return parser

def nondefault_trainer_args(opt):

    parser = argparse.ArgumentParser()
    parser = Trainer.add_argparse_args(parser)
    args = parser.parse_args([])

    return sorted(k for k in vars(args) if getattr(opt, k) != getattr(args, k))

if __name__ == "__main__":
    sys.path.append(os.getcwd())
    
    now = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")

    parser = get_parser()
    parser = Trainer.add_argparse_args(parser)

    opt, unknown = parser.parse_known_args()
    if opt.name and opt.resume:
        raise ValueError(
            "-n/--name and -r/--resume cannot be specified both."
            "If you want to resume training in a new log folder, "
            "use -n/--name in combination with --resume_from_checkpoint"
        )
    if opt.resume:
        if not os.path.exists(opt.resume):
            raise ValueError("Cannot find {}".format(opt.resume))
        if os.path.isfile(opt.resume):
            paths = opt.resume.split("/")
            idx = len(paths)-paths[::-1].index("logs")+1
            logdir = "/".join(paths[:idx])
            ckpt = opt.resume
        else:
            assert os.path.isdir(opt.resume), opt.resume
            logdir = opt.resume.rstrip("/")
            ckpt = os.path.join(logdir, "checkpoints", "last.ckpt")

        opt.resume_from_checkpoint = ckpt

        base_configs = sorted(glob.glob(os.path.join(logdir, "configs/*.yaml")))
        opt.base = base_configs+opt.base
        _tmp = logdir.split("/")
        name = _tmp[_tmp.index("logs")+1]
        nowname = _tmp[_tmp.index("logs")+2]
    
    else:
        if opt.name:
            name = opt.name
        elif opt.base:
            cfg_fname = os.path.split(opt.base[0])[-1]
            cfg_name = os.path.splitext(cfg_fname)[0]
            name = cfg_name.split('_')[0]
        else:
            name = "no_name"
        nowname = now

    configs = [OmegaConf.load(cfg) for cfg in opt.base]

    seed_everything(0)
    # merge configs
    cli = OmegaConf.from_dotlist(unknown)
    configs = OmegaConf.merge(*configs, cli)
    # define log directories
    logdir = os.path.join("logs",name, nowname)
    ckptdir = os.path.join(logdir, "checkpoints")
    cfgdir = os.path.join(logdir, "configs")
    configs.setup.logdir = logdir
    configs.setup.ckptdir = ckptdir 
    configs.setup.cfgdir = cfgdir 
    #### set up important trainer flags
    if configs.is_raw:
        configs.lightning.trainer.max_epochs = 1
    # merge trainer cli with config
    trainer_cfg = configs.lightning.get("trainer", OmegaConf.create())
    for k in nondefault_trainer_args(opt): # this incorporates cli into trainer configs
        trainer_cfg[k] = getattr(opt, k)
    
    if not "gpus" in trainer_cfg:
        cpu = True
    else:
        gpuinfo = trainer_cfg["gpus"]
        print(f"Running on GPUs {gpuinfo}")
        cpu = False

    trainer_opt = argparse.Namespace(**trainer_cfg)
    configs.lightning.trainer = trainer_cfg
    
    #### configure learning rate
    lr = configs.hparams.lr
    if not cpu:
        ngpu = len(configs.lightning.trainer.gpus.strip(",").split(','))
    else:
        ngpu = 0

    ### initialize pl model
    # model = LitModel(configs, configs.hparams)

    trainer_kwargs = dict()
    ### configure callbacks
    checkpoint_callback = ModelCheckpoint(dirpath=ckptdir,
                                        filename="{epoch:06}",
                                        verbose=True,
                                        save_last=True)
    setup_callback = SetupCallback(resume=opt.resume,
                                   now=now,
                                   logdir=logdir,
                                   ckptdir=ckptdir,
                                   cfgdir=cfgdir,
                                   config=configs)

    trainer_kwargs["callbacks"] = [checkpoint_callback,
                                   setup_callback]
    ### configure logger
    # logger = WandbLogger(project=configs.setup.wandb_name,
    #                      name=name+"_"+nowname,
    #                      id=nowname)

    # trainer_kwargs["logger"] = logger
    ### initialize trainer
    # trainer = Trainer.from_argparse_args(trainer_opt, 
    #                                     **trainer_kwargs,
    #                                     accelerator="gpu",
    #                                     devices=-1,
    #                                     plugins=DDPPlugin(find_unused_parameters=True))
                                    
    # trainer.fit(model)
    
        
    trainer = Trainer.from_argparse_args(trainer_opt, 
                                        **trainer_kwargs,
                                        accelerator="gpu",
                                        devices=-1,
                                        plugins=DDPPlugin(find_unused_parameters=True))
    model = LitModel(configs, configs.hparams)
                    
    trainer.fit(model)