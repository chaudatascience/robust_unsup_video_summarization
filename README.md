# robust_unsup_video_summarization

Original repo: https://github.com/pangzss/pytorch-CTVSUM

[Paper](https://openaccess.thecvf.com/content/WACV2023/papers/Pang_Contrastive_Losses_Are_Natural_Criteria_for_Unsupervised_Video_Summarization_WACV_2023_paper.pdf)  

[Supp](https://openaccess.thecvf.com/content/WACV2023/supplemental/Pang_Contrastive_Losses_Are_WACV_2023_supplemental.pdf) 



## Installation
```shell
git clone git@github.com:chaudatascience/robust_unsup_video_summarization.git
cd robust_unsup_video_summarization
conda env create -f environment.yml
conda activate ctvsum
```

## Datasets: 
Datasets are stored in 

`/projectnb/ivc-ml/chaupham/cs585_project/ctvsum/data`

copy this folder into robust_unsup_video_summarization folder.




## Training and Evaluation
### Evaluation with only pretrained features
1. In ./configs/aln_unif_config.yml, modify the dataset and evaluation settings, e.g.
```yaml
data:
  name: tvsum # summe
  setting: Canonical # Augmented/Transfer
```
2. Set
```yaml
is_raw: True
```
3. Set use Global Consistency or not
```yaml
use_unif: True # False
```
4. For Youtube8M features (quantized Inception), in ./configs/aln_unif_y8_config.yml, set
```yaml
is_raw: True
hparams:
  use_unif: True # False
```
5. Run
```shell
./run_ablation.sh
./run_y8.sh
```
### Contrastive refinement and evaluation
1. For TVSum and SumMe, set training/evaluation setting in ./configs/aln_unif_config.yml, and decide whether to use global consistency or uniqueness filter
```yaml
is_raw: False
use_unif: True # False
use_unq: True # False
```
  The code will run 5-fold cross validation by default.
  
2. For Youtube8M, similarly in ./configs/aln_unif_y8_config.yml,
```yaml
is_raw: False
hparams:
  use_unif: True # False
  use_unq: True # False
```
3. Run
```bash
./run_ablation.sh
./run_y8.sh
```
