"""
04_attention_fusion.py
Cross-modal Attention: Mel 임베딩 + Wav2vec 임베딩 → 가중 융합 벡터
"""
import torch
import torch.nn as nn
import torch.nn.functional as F


class CrossModalAttention(nn.Module):
    """
    Mel 임베딩을 Query, Wav2vec 임베딩을 Key/Value로 사용하는
    Cross-modal Attention Fusion
    """
    def __init__(self, mel_dim=256, w2v_dim=256, output_dim=256, num_heads=4):
        super().__init__()
        # Q/K/V 프로젝션
        self.q_proj = nn.Linear(mel_dim, output_dim)
        self.k_proj = nn.Linear(w2v_dim, output_dim)
        self.v_proj = nn.Linear(w2v_dim, output_dim)
        self.num_heads = num_heads
        self.head_dim = output_dim // num_heads
        self.scale = self.head_dim ** -0.5

        self.out_proj = nn.Linear(output_dim, output_dim)
        self.norm = nn.LayerNorm(output_dim)
        self.dropout = nn.Dropout(0.1)

    def forward(self, mel_emb, w2v_emb):
        """
        mel_emb: (B, mel_dim)
        w2v_emb: (B, w2v_dim)
        returns: fused_emb (B, output_dim)
        """
        B = mel_emb.size(0)

        # (B, 1, dim) → sequence dim 추가
        Q = self.q_proj(mel_emb).unsqueeze(1)   # (B, 1, output_dim)
        K = self.k_proj(w2v_emb).unsqueeze(1)   # (B, 1, output_dim)
        V = self.v_proj(w2v_emb).unsqueeze(1)   # (B, 1, output_dim)

        # Scaled dot-product attention
        attn_score = torch.bmm(Q, K.transpose(1, 2)) * self.scale  # (B, 1, 1)
        attn_weight = F.softmax(attn_score, dim=-1)                 # (B, 1, 1)
        attn_output = torch.bmm(attn_weight, V).squeeze(1)          # (B, output_dim)

        # Residual + LayerNorm
        fused = self.norm(mel_emb + self.dropout(self.out_proj(attn_output)))
        return fused  # (B, output_dim)


class FeatureFusion(nn.Module):
    """
    모든 특성 통합:
      - DDK 6차원  (ddk_rate, ddk_mean_dur_ms, ddk_regularity_ms,
                      pause_rate, pause_mean_dur_ms, pause_regularity_ms)
      - 성별 1차원
      - Mel 임베딩 (mel_dim=256)
      - Attention 융합 벡터 (output_dim=256)
    → Concatenate → 입력 총 차원: 6+1+256+256 = 519
    """
    def __init__(self, ddk_dim=12, gender_dim=1, mel_dim=256,
                 w2v_dim=256, fusion_dim=256):
        super().__init__()
        self.attention = CrossModalAttention(
            mel_dim=mel_dim,
            w2v_dim=w2v_dim,
            output_dim=fusion_dim,
        )
        self.total_dim = ddk_dim + gender_dim + mel_dim + fusion_dim
        # 기본값: 12+1+256+256 = 525

    def forward(self, ddk_feat, gender, mel_emb, w2v_emb):
        """
        ddk_feat:  (B, 12)
        gender:    (B, 1)
        mel_emb:   (B, mel_dim)
        w2v_emb:   (B, w2v_dim)
        returns:   (B, total_dim)
        """
        fused = self.attention(mel_emb, w2v_emb)  # (B, fusion_dim)
        out = torch.cat([ddk_feat, gender, mel_emb, fused], dim=1)
        return out


if __name__ == "__main__":
    B = 4
    ddk = torch.randn(B, 12)  # 12-dim DDK
    gender = torch.zeros(B, 1)
    mel_emb = torch.randn(B, 256)
    w2v_emb = torch.randn(B, 256)

    fusion = FeatureFusion()
    out = fusion(ddk, gender, mel_emb, w2v_emb)
    print(f"융합 벡터 shape: {out.shape}")  # (4, 12+1+256+256=525)
