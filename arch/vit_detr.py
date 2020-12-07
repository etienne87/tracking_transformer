"""
Transformer for Detection 
"""
import torch
import torch.nn as nn
import torch.nn.functional as f

from core.transformer import Transformer
from core.reversible_transformer import ReversibleTransformer
from core.positional_encoding import FixedPositionalEncoding, LearnedPositionalEncoding
from core.pooling import QuerySetAttention, SlotAttention, FunnelLayer2d
from einops import rearrange


from arch.cnn import CNN


class DetViT(nn.Module):
    def __init__(self, in_channels, out_channels, hybrid=False, patch_dim=16, num_layers=2, num_heads=32, num_queries=8, embedding_dim=512, hidden_dim=512, max_len=512, dropout=0.):
        super().__init__()

        self.patch_dim = patch_dim

        self.flatten_dim_in = patch_dim * patch_dim * in_channels
        self.linear_encoding = nn.Linear(self.flatten_dim_in, embedding_dim)

        self.position_encoding = LearnedPositionalEncoding(max_len, embedding_dim)
        #self.position_encoding = FixedPositionalEncoding(max_len, embedding_dim)
        self.encoder = Transformer(embedding_dim, num_layers, num_heads, hidden_dim, dropout)
        # self.encoder = ReversibleTransformer(embedding_dim, num_layers, num_heads, hidden_dim, dropout)

        self.pool = QuerySetAttention(num_queries, embedding_dim, num_heads) 

        # Requires smaller learning rate
        #self.pool = SlotAttention(num_queries, embedding_dim, iters=3, hidden_dim=hidden_dim)
        #self.pool = lambda x:x

        self.linear_decoding = nn.Linear(embedding_dim, out_channels)
        self.decoder = Transformer(embedding_dim, 2, num_heads, hidden_dim, dropout)
        # self.decoder = ReversibleTransformer(embedding_dim, num_layers, num_heads, hidden_dim, dropout)

        if hybrid:
            self.features = CNN(in_channels, embedding_dim, 3)

    def forward(self, x):
        b,c,h,w = x.shape
        p = self.patch_dim

        if hasattr(self, 'features'):
            x = self.features(x)
        else:
            x = rearrange(x, 'b c (h p1) (w p2) -> b (h w) (p1 p2 c)', p1 = p, p2 = p)
            x = self.linear_encoding(x)

        x = self.position_encoding(x)
        x = self.encoder(x)
        x = self.pool(x)
        x = self.decoder(x)
        y = self.linear_decoding(x)
        return y


if __name__ == '__main__':
    x = torch.randn(2,3,128,128)
    net = DetViT(3, 11, num_layers=4)
    y = net(x)
    print(y.shape)
