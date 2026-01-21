import re #txt cleaning
import torch
import torch.nn as nn
import torch.nn.functional as F
import sqlite3
import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModel

# ==========================================
# 1. KONFIGURASI & PREPROCESSING
# ==========================================

MODEL_PATH = "/Users/mac/Documents/ITS/BISMILLAH_TA/modelll/full/model_prompt_3_qwk_0_7879.pth"

class Config:
    BERT_MODEL_NAME = "indobenchmark/indobert-base-p1"
    MAX_SEQ_LENGTH = 128
    LSTM_HIDDEN_DIM = 100
    DROPOUT = 0.124
    ATTENTION_HEADS = 2
    ATTENTION_HIDDEN = 100
    DEVICE = torch.device("cpu")

def clean_text(text):
    if not isinstance(text, str):
        return ""
    # 1. Lowercase
    text = text.lower()
    # 2. Hapus karakter tidak relevan
    text = re.sub(r'[^a-z0-9\s\.,!?()"\'-]', ' ', text)
    # 3. Hapus spasi berlebih
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ==========================================
# 2. ARSITEKTUR MODEL
# ==========================================
# mendefinisikan ulang class agar .pth bisa di-load

# mengubah 128 token jadi 1 vektor representasi
class StrictAttentionPooling(nn.Module):
    def __init__(self, input_dim, hidden_dim):
        super().__init__()
        self.W_ha = nn.Linear(input_dim, hidden_dim)
        self.W_h = nn.Linear(hidden_dim, 1, bias=False)

    def forward(self, h):
        h_bar = torch.tanh(self.W_ha(h))
        scores = self.W_h(h_bar)
        attn_weights = F.softmax(scores, dim=1)
        context = torch.sum(h * attn_weights, dim=1)
        return context

class IndoBERTPromptAwareAES(nn.Module):
    def __init__(self, model_name=Config.BERT_MODEL_NAME, hidden_dim=Config.LSTM_HIDDEN_DIM):
        super(IndoBERTPromptAwareAES, self).__init__()
        self.essay_bert = AutoModel.from_pretrained(model_name)
        self.context_bert = AutoModel.from_pretrained(model_name)
        emb_dim = self.essay_bert.config.hidden_size #768

        self.lstm_essay = nn.LSTM(emb_dim, hidden_dim, batch_first=True, bidirectional=True)
        self.att_pool_paf = StrictAttentionPooling(hidden_dim * 2, hidden_dim) #attention pooling
        self.linear_paf = nn.Linear(hidden_dim * 4, hidden_dim) #fusion layer

        # proyeksi multi head attention
        self.proj_essay_mha = nn.Linear(emb_dim, Config.ATTENTION_HIDDEN) 
        self.proj_prompt_mha = nn.Linear(emb_dim, Config.ATTENTION_HIDDEN)

        # mha
        self.multihead_attn = nn.MultiheadAttention( 
            embed_dim=Config.ATTENTION_HIDDEN,
            num_heads=Config.ATTENTION_HEADS,
            batch_first=True,
            dropout=Config.DROPOUT
        )

        self.lstm_adh = nn.LSTM(Config.ATTENTION_HIDDEN, hidden_dim, batch_first=True, bidirectional=True)
        self.att_pool_adh = StrictAttentionPooling(hidden_dim * 2, hidden_dim)
        self.linear_adh = nn.Linear(hidden_dim * 2, 1)
        self.final_regressor = nn.Linear(hidden_dim + 1, 1)
        self.sigmoid = nn.Sigmoid()
        self.dropout = nn.Dropout(Config.DROPOUT)

    def forward(self, input_ids_essay, attention_mask_essay, input_ids_prompt, attention_mask_prompt):
        out_essay = self.essay_bert(input_ids_essay, attention_mask=attention_mask_essay).last_hidden_state
        out_prompt = self.context_bert(input_ids_prompt, attention_mask=attention_mask_prompt).last_hidden_state
        H = self.dropout(out_essay)
        P_emb = self.dropout(out_prompt)

        # Path 1
        lstm_out_essay, _ = self.lstm_essay(H)
        r_att = self.att_pool_paf(lstm_out_essay)
        mask_expanded = attention_mask_essay.unsqueeze(-1).expand(lstm_out_essay.size()).float()
        sum_embeddings = torch.sum(lstm_out_essay * mask_expanded, dim=1)
        sum_mask = torch.clamp(mask_expanded.sum(dim=1), min=1e-9)
        r_ave = sum_embeddings / sum_mask
        r_concat = torch.cat((r_att, r_ave), dim=1)
        S_paf = self.linear_paf(r_concat)

        # Path 2
        H_proj = self.proj_essay_mha(H)
        P_proj = self.proj_prompt_mha(P_emb)
        key_mask = (attention_mask_essay == 0)
        A_pea, _ = self.multihead_attn(query=P_proj, key=H_proj, value=H_proj, key_padding_mask=key_mask)
        lstm_out_adh, _ = self.lstm_adh(A_pea)
        feat_adh_pooled = self.att_pool_adh(lstm_out_adh)
        S_pea = self.sigmoid(self.linear_adh(feat_adh_pooled))

        # Final
        R_gen = torch.cat((S_paf, S_pea), dim=1)
        y = self.sigmoid(self.final_regressor(R_gen))
        return y, R_gen

# ==========================================
# 3. SETUP API & LOAD MODEL
# ==========================================

print("Sedang memuat Tokenizer & Model... (Mohon tunggu)")
tokenizer = AutoTokenizer.from_pretrained(Config.BERT_MODEL_NAME)
model = IndoBERTPromptAwareAES()

# Load Weights
try:
    # map_location='cpu' 
    checkpoint = torch.load(MODEL_PATH, map_location=Config.DEVICE) 
    
    # Handle jika yang tersimpan adalah checkpoint full (ada optimizer dll) atau state_dict saja
    if isinstance(checkpoint, dict) and 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
    else:
        model.load_state_dict(checkpoint)
        
    model.to(Config.DEVICE)
    model.eval()
    print(">> MODEL BERHASIL DI-LOAD!")
except Exception as e:
    print(f">> ERROR LOAD MODEL: {e}")
    print("Pastikan path MODEL_PATH di baris atas sudah benar.")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5174", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database Setup
def init_db():
    conn = sqlite3.connect('aes_history.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (id INTEGER PRIMARY KEY, timestamp TEXT, pertanyaan TEXT, 
                  kunci_jawaban TEXT, jawaban TEXT, max_score INTEGER, predicted_score REAL)''')
    conn.commit()
    conn.close()

init_db()

class EssayInput(BaseModel):
    pertanyaan: str
    kunci_jawaban: str
    jawaban: str
    max_score: int

@app.post("/predict")
async def predict_score(data: EssayInput):
    try:
        # 1. Cleaning
        clean_jawaban = clean_text(data.jawaban)
        clean_pertanyaan = clean_text(data.pertanyaan)
        clean_kunci = clean_text(data.kunci_jawaban)
        
        # 2. Tokenizing
        # Essay
        essay_enc = tokenizer(
            clean_jawaban, 
            max_length=Config.MAX_SEQ_LENGTH, 
            padding='max_length', 
            truncation=True, 
            return_tensors='pt'
        )
        
        # Prompt (Pertanyaan + SEP + Kunci)
        prompt_text = clean_pertanyaan + " [SEP] " + clean_kunci
        prompt_enc = tokenizer(
            prompt_text, 
            max_length=Config.MAX_SEQ_LENGTH, 
            padding='max_length', 
            truncation=True, 
            return_tensors='pt'
        )

        # 3. Inference
        with torch.no_grad():
            input_ids_essay = essay_enc['input_ids'].to(Config.DEVICE)
            mask_essay = essay_enc['attention_mask'].to(Config.DEVICE)
            input_ids_prompt = prompt_enc['input_ids'].to(Config.DEVICE)
            mask_prompt = prompt_enc['attention_mask'].to(Config.DEVICE)

            # Forward pass
            y_pred_norm, _ = model(input_ids_essay, mask_essay, input_ids_prompt, mask_prompt)
            
            # Output model adalah sigmoid (0-1)
            normalized_score = y_pred_norm.item()
            
            # 4. Denormalize (Scale ke Max Score user)
            final_score = normalized_score * data.max_score
            final_score = round(final_score)

        # 5. Simpan ke History
        conn = sqlite3.connect('aes_history.db')
        c = conn.cursor()
        c.execute("INSERT INTO history (timestamp, pertanyaan, kunci_jawaban, jawaban, max_score, predicted_score) VALUES (?, ?, ?, ?, ?, ?)",
                  (datetime.datetime.now().isoformat(), data.pertanyaan, data.kunci_jawaban, data.jawaban, data.max_score, final_score))
        conn.commit()
        conn.close()

        return {
            "predicted_score": final_score,
            "max_score": data.max_score,
            "raw_normalized": normalized_score # Debug info
        }

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_history():
    conn = sqlite3.connect('aes_history.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM history")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]