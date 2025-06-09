# File: run_training_standalone.py

import argparse
import json
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
from tqdm import tqdm
import os
import math

# ==============================================================================
# 1. MODEL ARCHITECTURE (Copied directly into this file)
# ==============================================================================


class PositionalEncoding(nn.Module):
    """Standard sinusoidal positional encoding."""

    def __init__(
        self, d_model: int, dropout: float = 0.1, max_len: int = 5000
    ):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        position = torch.arange(max_len).unsqueeze(1)
        div_term = torch.exp(
            torch.arange(0, d_model, 2) * (-math.log(10000.0) / d_model)
        )
        pe = torch.zeros(max_len, 1, d_model)
        pe[:, 0, 0::2] = torch.sin(position * div_term)
        pe[:, 0, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.transpose(0, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Args: x: Tensor, shape [batch_size, seq_len, embedding_dim]"""
        # The slice of self.pe must match the sequence length of x
        x = x + self.pe[:, : x.size(1)]
        return self.dropout(x)


class CircuitFormer(nn.Module):
    """
    An Encoder-Only Transformer model to predict quantum circuit fidelity.
    It processes a sequence of rich gate feature vectors.
    """

    def __init__(
        self,
        feature_dim: int,
        model_dim: int,
        n_heads: int,
        n_layers: int,
        dropout: float,
        max_seq_len: int,
    ):
        """
        Args:
            feature_dim (int): The dimensionality of the input feature vector for each gate.
            model_dim (int): The internal dimensionality of the Transformer (d_model).
            n_heads (int): The number of attention heads.
            n_layers (int): The number of stacked Transformer encoder layers.
            dropout (float): The dropout rate.
            max_seq_len (int): The maximum sequence length the model can handle.
        """
        super().__init__()
        # print(f"--- Model Instantiation ---")
        # print(f"DEBUG: CircuitFormer class received max_seq_len = {max_seq_len}")

        self.model_dim = model_dim
        self.input_projection = nn.Linear(feature_dim, model_dim)
        self.cls_token = nn.Parameter(torch.randn(1, 1, model_dim))

        # This is where the positional encoding table size is determined.
        # It must be based on the max_seq_len of the *data* + 1 for the CLS token.
        self.pos_encoder = PositionalEncoding(
            model_dim, dropout, max_len=max_seq_len + 1
        )
        # print(f"DEBUG: PositionalEncoding created with max_len = {max_seq_len + 1}")

        encoder_layer = nn.TransformerEncoderLayer(
            d_model=model_dim, nhead=n_heads, dropout=dropout, batch_first=True
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer, num_layers=n_layers
        )
        self.classifier_head = nn.Sequential(
            nn.LayerNorm(model_dim),
            nn.Linear(model_dim, model_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(model_dim // 2, 1),
            nn.Sigmoid(),
        )

    def forward(self, src: torch.Tensor) -> torch.Tensor:
        """Args: src: Tensor, shape [batch_size, seq_len, feature_dim]"""
        src = self.input_projection(src)
        cls_tokens = self.cls_token.expand(src.shape[0], -1, -1)
        x = torch.cat(
            (cls_tokens, src), dim=1
        )  # Shape becomes [batch_size, seq_len+1, model_dim]
        x = self.pos_encoder(x)
        encoded_output = self.transformer_encoder(x)
        cls_output = encoded_output[:, 0]
        prediction = self.classifier_head(cls_output)
        return prediction


# ==============================================================================
# 2. DATASET CLASS (Copied directly into this file)
# ==============================================================================


class FidelityDataset(Dataset):
    """
    A PyTorch Dataset class that also handles padding and truncation.
    """

    def __init__(self, raw_data, max_seq_len: int, feature_dim: int):
        self.data = raw_data
        self.max_len = max_seq_len
        self.feature_dim = feature_dim

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]

        # --- PADDING & TRUNCATION LOGIC ---
        feature_sequence = item["feature_tensor"]

        # 1. Truncate if too long
        if len(feature_sequence) > self.max_len:
            feature_sequence = feature_sequence[: self.max_len]

        # 2. Pad with zeros if too short
        padding_needed = self.max_len - len(feature_sequence)
        if padding_needed > 0:
            # Create a list of zero vectors for padding
            zero_vector = [0.0] * self.feature_dim
            padding = [zero_vector] * padding_needed
            feature_sequence.extend(padding)

        # Convert to tensor *after* ensuring correct size
        feature_tensor = torch.tensor(feature_sequence, dtype=torch.float32)

        fidelity_label = torch.tensor(
            [item["fidelity_label"]], dtype=torch.float32
        )

        return feature_tensor, fidelity_label


# ==============================================================================
# 3. MAIN TRAINING LOGIC (Copied from your script)
# ==============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="trainer for CircuitFormer.")
    # (All your argparse arguments are the same)
    parser.add_argument("--dataset-path", type=str, required=True)
    parser.add_argument("--output-dir", type=str, default="trained_models")
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--learning-rate", type=float, default=0.0001)
    parser.add_argument("--feature-dim", type=int, default=16)
    parser.add_argument("--model-dim", type=int, default=64)
    parser.add_argument("--n-heads", type=int, default=4)
    parser.add_argument("--n-layers", type=int, default=4)
    parser.add_argument(
        "--max-seq-len", type=int, default=256
    )  # This should now be the only source of truth

    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"--- Using device: {device} ---")

    print(f"Loading dataset from: {args.dataset_path}")
    with open(args.dataset_path, "r") as f:
        raw_data = json.load(f)
    print(f"Loaded {len(raw_data)} samples.")

    full_dataset = FidelityDataset(
        raw_data, max_seq_len=args.max_seq_len, feature_dim=args.feature_dim
    )
    train_size = int(0.8 * len(full_dataset))
    val_size = len(full_dataset) - train_size
    train_dataset, val_dataset = random_split(
        full_dataset, [train_size, val_size]
    )

    train_loader = DataLoader(
        train_dataset, batch_size=args.batch_size, shuffle=True, num_workers=0
    )
    val_loader = DataLoader(
        val_dataset, batch_size=args.batch_size, num_workers=0
    )

    print(
        f"Training set size: {len(train_dataset)}, Validation set size: {len(val_dataset)}"
    )

    # Initialize model using keyword arguments for safety
    model = CircuitFormer(
        feature_dim=args.feature_dim,
        model_dim=args.model_dim,
        n_heads=args.n_heads,
        n_layers=args.n_layers,
        dropout=0.1,
        max_seq_len=args.max_seq_len,
    ).to(device)

    criterion = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=args.learning_rate)
    # Add the scheduler after the optimizer
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, T_max=args.epochs * len(train_loader)
    )

    print("\n--- Starting Model Training ---")
    best_val_loss = float("inf")

    # Mixed precision training setup
    scaler = torch.amp.GradScaler()

    for epoch in range(args.epochs):
        model.train()
        train_pbar = tqdm(
            train_loader, desc=f"Epoch {epoch + 1}/{args.epochs} [Training]"
        )
        for features, labels in train_pbar:
            features, labels = features.to(device), labels.to(device)

            # Using mixed precision
            with torch.cuda.amp.autocast():
                outputs = model(features)
                loss = criterion(outputs, labels)

            optimizer.zero_grad()
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()

            train_pbar.set_postfix(loss=f"{loss.item():.5f}")

        # -- Validation Phase --
        model.eval()
        total_val_loss = 0.0
        with torch.no_grad():
            for features, labels in val_loader:
                features, labels = features.to(device), labels.to(device)
                with torch.cuda.amp.autocast():
                    outputs = model(features)
                    loss = criterion(outputs, labels)
                total_val_loss += loss.item()

        avg_val_loss = total_val_loss / len(val_loader)
        print(
            f"Epoch {epoch + 1}/{args.epochs} | Val Loss: {avg_val_loss:.5f}"
        )

        if avg_val_loss < best_val_loss:
            best_val_loss = avg_val_loss
            torch.save(
                model.state_dict(),
                os.path.join(args.output_dir, "best_model.pth"),
            )
            print("  -> New best model saved.")

    print("\n--- Training Complete ---")
