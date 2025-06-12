## Create env & installation
```
conda create -n ucc_ai python=3.12
conda activate ucc_ai


pip install ucc
cd ucc
uv sync --all-extras --all-groups
pip install torch
pip install tqdm
```


## Generate Random qasm2 Circuit
```
# Generate 5000 samples with default settings (max 15 qubits)
python scripts/generate_dataset.py --num-samples 5000

# Generate a smaller test dataset with smaller circuits
python ucc\noise_aware\ml_model\generate_dataset.py --num-samples 1000 --max-qubits 8 --output-file small_test_dataset.json
```

## Train
```
# Create the output directory first
mkdir -p trained_models

# Run the training script
python ucc\noise_aware\ml_model\train_model.py --dataset-path diverse_fidelity_dataset.json --epochs 50 --batch-size 128 --learning-rate 0.0001
```

## My attempt with 8gb intel i8 rtx1050
```
python ucc/noise_aware/ml_model/generate_dataset.py ^
    --num-samples 10_000 ^
    --max-qubits 100 ^
    --min-qubits 4 ^
    --output-file C:/Users/junli/ucc/ucc/noise_aware/ml_model/diverse_fidelity_dataset.json ^
    --max-seq-len 2048
```
Dataset Composition:
- EfficientSU2: 1211 samples (24.2%)
- random: 1251 samples (25.0%)
- qft: 2034 samples (40.7%)
- qv: 504 samples (10.1%)

model-dim * n-heads must be the same as embed_dim
```
python ucc/noise_aware/ml_model/train_model.py ^
    --dataset-path C:/Users/junli/ucc/ucc/noise_aware/ml_model/diverse_fidelity_dataset.json ^
    --output-dir C:/Users/junli/ucc/ucc/noise_aware/ml_model/trained_models_medium_reliable/ ^
    --epochs 30 ^
    --batch-size 128 ^
    --learning-rate 0.0001 ^
    --patience 5 ^
    --min-delta 0.00001 ^
    --model-dim 256 ^
    --n-heads 8 ^
    --n-layers 6 ^
    --max-seq-len 512
```

## google/kaggle collab

```
!git clone --single-branch --branch noise_aware-passes https://github.com/poig/ucc.git
from google.colab import drive
drive.mount('/content/drive')
!pip install -q qiskit qiskit_ibm_runtime
```

```
python /content/ucc/ucc/noise_aware/ml_model/generate_dataset.py ^
--num-samples 10_000 ^
--max-qubits 20 ^
--min-qubits 4 ^
--output-file /content/ucc/ucc/noise_aware/ml_model/10k_dataset.json ^
--max-seq-len 1024

(1.7GB)

--- Initializing Backend and Noise Models ---
Initialized with backend: fake_washington (127 qubits)
Feature vector dimension is set to: 16

--- Generating 10000 Data Samples from Diverse Portfolio ---
Generating Circuits: 100% 10000/10000 [37:50<00:00,  4.40it/s]

--- Dataset Generation Complete ---
Successfully created 7940 samples.
Saved to '/content/ucc/ucc/noise_aware/ml_model/10k_dataset.json'

Dataset Composition:
- qcnn: 1497 samples (18.9%)
- qft: 2550 samples (32.1%)
- qv: 386 samples (4.9%)
- EfficientSU2: 2522 samples (31.8%)
- random: 985 samples (12.4%)
```

Thanks to kaggle! I can use 2*T4 GPU for 30 hours each week!!!

each epochs are roughly 1 minute, and just 3 epochs its trained to its best 1th loss value!!!

which are enough to train this monster,

you can see how good the model calibrate to 10k quantum circuit,

I hope we have a open-source pre-generate dataset of these circuit information, to make these trian more robust
```
# python /kaggle/ucc/ucc/noise_aware/ml_model/train_model.py ^
#     --dataset-path /kaggle/input/ai-router-passes-10k-dataset/10k_dataset.json ^
#     --output-dir /kaggle/model/ ^
#     --epochs 50 ^
#     --batch-size 64 ^
#     --learning-rate 0.0001 ^
#     --patience 7 ^
#     --min-delta 0.000005 ^
#     --model-dim 256 ^
#     --n-heads 8 ^
#     --n-layers 8 ^
#     --max-seq-len 1024

output:

--- Using device: cuda ---
Loading dataset from: /kaggle/input/ai-router-passes-10k-dataset/10k_dataset.json
Loaded 7940 samples. Training on 6352, validating on 1588.
/kaggle/ucc/ucc/noise_aware/ml_model/train_model.py:289: FutureWarning: `torch.cuda.amp.GradScaler(args...)` is deprecated. Please use `torch.amp.GradScaler('cuda', args...)` instead.
  scaler = torch.cuda.amp.GradScaler(

--- Starting Model Training ---
Epoch 01/50 | Train Loss: 0.004304 | Val Loss: 0.000061
  -> Val loss improved from inf to 0.000061. Saving model...
Epoch 02/50 | Train Loss: 0.000045 | Val Loss: 0.000012
  -> Val loss improved from 0.000061 to 0.000012. Saving model...
Epoch 03/50 | Train Loss: 0.000010 | Val Loss: 0.000002
  -> Val loss improved from 0.000012 to 0.000002. Saving model...
Epoch 04/50 | Train Loss: 0.000003 | Val Loss: 0.000001
Epoch 05/50 | Train Loss: 0.000002 | Val Loss: 0.000000
Epoch 06/50 | Train Loss: 0.000001 | Val Loss: 0.000000
Epoch 07/50 | Train Loss: 0.000001 | Val Loss: 0.000000
Epoch 08/50 | Train Loss: 0.000001 | Val Loss: 0.000000
Epoch 09/50 | Train Loss: 0.000001 | Val Loss: 0.000000
Epoch 10/50 | Train Loss: 0.000001 | Val Loss: 0.000000

--- Early Stopping Triggered ---
Validation loss has not improved for 7 consecutive epochs.

--- Training Complete ---
Best validation loss achieved: 0.000002
Best model saved to: /kaggle/model/best_model.pth
```

run ucc-bench layout benchmarking
```
uv run ucc-bench C:\Users\junli\ucc-bench\benchmarks\layout_benchmarks.toml
```
