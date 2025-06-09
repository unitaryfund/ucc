import argparse
import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
from tqdm import tqdm
import os

# Import our CircuitFormer model architecture
from ucc.noise_aware.ml_model.circuit_former import CircuitFormer


# --- The PyTorch Dataset Class ---
class FidelityDataset(Dataset):
    """
    A PyTorch Dataset class to load our pre-processed circuit data.
    """

    def __init__(self, raw_data):
        self.data = raw_data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]

        # Load the data from our JSON format
        feature_tensor = torch.tensor(
            item["feature_tensor"], dtype=torch.float32
        )
        fidelity_label = torch.tensor(
            [item["fidelity_label"]], dtype=torch.float32
        )

        return feature_tensor, fidelity_label


# --- MAIN EXECUTION BLOCK ---

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Train the CircuitFormer fidelity prediction model."
    )
    parser.add_argument(
        "--dataset-path",
        type=str,
        required=True,
        help="Path to the JSON dataset file.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="trained_models",
        help="Directory to save the trained model and logs.",
    )
    parser.add_argument(
        "--epochs", type=int, default=25, help="Number of training epochs."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Batch size for training and validation.",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=1e-4,
        help="Learning rate for the Adam optimizer.",
    )
    # --- Model Hyperparameters ---
    # These must match the data generation script and model architecture
    parser.add_argument(
        "--feature-dim",
        type=int,
        default=16,
        help="Dimension of the gate feature vector.",
    )
    parser.add_argument(
        "--model-dim",
        type=int,
        default=128,
        help="Internal dimension of the Transformer.",
    )
    parser.add_argument(
        "--n-heads", type=int, default=8, help="Number of attention heads."
    )
    parser.add_argument(
        "--n-layers",
        type=int,
        default=6,
        help="Number of Transformer encoder layers.",
    )
    parser.add_argument(
        "--max-seq-len",
        type=int,
        default=512,
        help="Max sequence length for the model.",
    )

    args = parser.parse_args()
    # --- Setup ---
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)

    # Set the device (use GPU if available, otherwise CPU)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"--- Using device: {device} ---")

    # --- 1. Load Data ---
    print(f"Loading dataset from: {args.dataset_path}")
    with open(args.dataset_path, "r") as f:
        raw_data = json.load(f)
    print(f"Loaded {len(raw_data)} samples.")

    # --- 2. Create Datasets and DataLoaders ---
    full_dataset = FidelityDataset(raw_data)

    # Split into training (80%) and validation (20%) sets
    train_size = int(0.8 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_dataset, val_dataset = random_split(
        full_dataset, [train_size, val_size]
    )

    train_loader = DataLoader(
        train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=4
    )
    val_loader = DataLoader(
        val_dataset, batch_size=args.batch_size, num_workers=4
    )

    print(
        f"Training set size: {len(train_dataset)}, Validation set size: {len(val_dataset)}"
    )

    # --- 3. Initialize Model, Loss Function, and Optimizer ---
    model = CircuitFormer(
        feature_dim=args.feature_dim,
        model_dim=args.model_dim,
        n_heads=args.n_heads,
        n_layers=args.n_layers,
        max_seq_len=args.max_seq_len + 1,  # +1 for the [CLS] token
    ).to(device)

    # We use Mean Squared Error as it's a regression problem
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=args.learning_rate)

    print("\n--- Starting Model Training ---")
    best_val_loss = float("inf")
    training_log = []

    for epoch in range(args.epochs):
        # -- Training Phase --
        model.train()
        total_train_loss = 0.0
        train_pbar = tqdm(
            train_loader, desc=f"Epoch {epoch + 1}/{args.epochs} [Training]"
        )

        for features, labels in train_pbar:
            features, labels = features.to(device), labels.to(device)

            # Forward pass
            outputs = model(features)
            loss = criterion(outputs, labels)

            # Backward pass and optimization
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_train_loss += loss.item()
            train_pbar.set_postfix(loss=f"{loss.item():.5f}")

        avg_train_loss = total_train_loss / len(train_loader)

        # -- Validation Phase --
        model.eval()
        total_val_loss = 0.0
        with torch.no_grad():
            for features, labels in val_loader:
                features, labels = features.to(device), labels.to(device)
                outputs = model(features)
                loss = criterion(outputs, labels)
                total_val_loss += loss.item()

        avg_val_loss = total_val_loss / len(val_loader)

        print(
            f"Epoch {epoch + 1}/{args.epochs} | Train Loss: {avg_train_loss:.5f} | Val Loss: {avg_val_loss:.5f}"
        )

        log_entry = {
            "epoch": epoch + 1,
            "train_loss": avg_train_loss,
            "val_loss": avg_val_loss,
        }
        training_log.append(log_entry)

        # --- 4. Checkpointing: Save the best model found so far ---
        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            model_path = os.path.join(
                args.output_dir, "best_circuit_former_model.pth"
            )
            torch.save(model.state_dict(), model_path)
            print(
                f"  -> New best model saved to {model_path} (Val Loss: {best_val_loss:.5f})"
            )

    # --- 5. Save Final Artifacts ---
    # Save the final model state
    final_model_path = os.path.join(
        args.output_dir, "final_circuit_former_model.pth"
    )
    torch.save(model.state_dict(), final_model_path)

    # Save the training log
    log_path = os.path.join(args.output_dir, "training_log.json")
    with open(log_path, "w") as f:
        json.dump(training_log, f, indent=2)

    # Save the config used for this training run
    config_path = os.path.join(args.output_dir, "training_config.json")
    with open(config_path, "w") as f:
        json.dump(vars(args), f, indent=2)

    print("\n--- Training Complete ---")
    print(f"Best validation loss achieved: {best_val_loss:.5f}")
    print(f"Final model, best model, and logs saved in '{args.output_dir}'")
