import torch
import torch.nn as nn
import math


class PositionalEncoding(nn.Module):
    """
    Standard sinusoidal positional encoding, as used in the original Transformer paper.
    This injects information about the relative or absolute position of the tokens.
    """

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
        self.register_buffer(
            "pe", pe.transpose(0, 1)
        )  # Shape: (1, max_len, d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: Tensor, shape [batch_size, seq_len, embedding_dim]
        """
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
        dropout: float = 0.1,
        max_seq_len: int = 512,
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
        self.model_dim = model_dim

        # 1. Input Projection Layer
        self.input_projection = nn.Linear(feature_dim, model_dim)

        # 2. Special [CLS] token for classification/regression
        self.cls_token = nn.Parameter(torch.randn(1, 1, model_dim))

        # 3. Positional Encoder
        self.pos_encoder = PositionalEncoding(
            model_dim, dropout, max_len=max_seq_len
        )

        # 4. Transformer Encoder Stack
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=model_dim,
            nhead=n_heads,
            dropout=dropout,
            batch_first=True,  # Crucial for (batch, seq, feature) input shape
        )
        self.transformer_encoder = nn.TransformerEncoder(
            encoder_layer, num_layers=n_layers
        )

        # 5. The final Regression Head
        self.classifier_head = nn.Sequential(
            nn.LayerNorm(model_dim),
            nn.Linear(model_dim, model_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(model_dim // 2, 1),
            nn.Sigmoid(),  # Squash output to be between 0 and 1
        )

    def forward(self, src: torch.Tensor) -> torch.Tensor:
        """
        Args:
            src: The source sequence tensor.
                 Shape: [batch_size, seq_len, feature_dim]

        Returns:
            A tensor of predicted fidelities. Shape: [batch_size, 1]
        """
        # Project input features to the model's dimension
        src = self.input_projection(
            src
        )  # Shape: [batch_size, seq_len, model_dim]

        # Prepend the [CLS] token to each sequence in the batch
        cls_tokens = self.cls_token.expand(src.shape[0], -1, -1)
        x = torch.cat(
            (cls_tokens, src), dim=1
        )  # Shape: [batch_size, seq_len+1, model_dim]

        # Add positional encoding
        x = self.pos_encoder(x)

        # Pass through the Transformer encoder
        encoded_output = self.transformer_encoder(
            x
        )  # Shape: [batch_size, seq_len+1, model_dim]

        # Extract the output of the [CLS] token (it's always the first token)
        cls_output = encoded_output[:, 0]  # Shape: [batch_size, model_dim]

        # Get the final prediction
        prediction = self.classifier_head(cls_output)

        return prediction
