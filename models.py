import torch
import torch.nn as nn

class AQIClassifier(nn.Module):
    def __init__(self, export=False):
        super().__init__()
        self.export = export
        self.net = nn.Sequential(
            nn.Linear(8, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, 4)
        )
        
    def forward(self, x):
        logits = self.net(x)
        if self.export:
            return torch.softmax(logits, dim=1)
        return logits

class AnomalyDetector(nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(8, 16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.ReLU(),
            nn.Linear(8, 4),
            nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.Linear(4, 8),
            nn.ReLU(),
            nn.Linear(8, 16),
            nn.ReLU(),
            nn.Linear(16, 8),
            nn.Sigmoid()
        )
        
    def forward(self, x):
        return self.decoder(self.encoder(x))

class CustomLSTM(nn.Module):
    def __init__(self, input_size, hidden_size):
        super().__init__()
        self.hidden_size = hidden_size
        self.gate_linear = nn.Linear(input_size + hidden_size, 4 * hidden_size)

    def forward(self, x):
        # Native PyTorch check: if exporting to ONNX, force static batch size 1
        if torch.onnx.is_in_onnx_export():
            batch_size = 1
        else:
            batch_size = x.size(0)
            
        h = torch.zeros(batch_size, self.hidden_size, device=x.device)
        c = torch.zeros(batch_size, self.hidden_size, device=x.device)
        
        seq_len = x.shape[1]
        for t in range(seq_len):
            xt = x[:, t, :]
            combined = torch.cat([xt, h], dim=1)
            gates = self.gate_linear(combined)
            
            # Slices instead of chunk/split prevents dynamic shape propagation errors in onnx2tf
            i = gates[:, 0:32]
            f = gates[:, 32:64]
            g = gates[:, 64:96]
            o = gates[:, 96:128]
            
            i = torch.sigmoid(i)
            f = torch.sigmoid(f)
            g = torch.tanh(g)
            o = torch.sigmoid(o)
            
            c = f * c + i * g
            h = o * torch.tanh(c)
            
        return h

class AQIPredictor(nn.Module):
    def __init__(self):
        super().__init__()
        self.lstm = CustomLSTM(input_size=8, hidden_size=32)
        self.head = nn.Sequential(
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 1)
        )
        
    def forward(self, x):
        out = self.lstm(x)
        return self.head(out)

class AQIRecommender(nn.Module):
    def __init__(self, export=False):
        super().__init__()
        self.export = export
        self.net = nn.Sequential(
            nn.Linear(4, 32),
            nn.ReLU(),
            nn.Linear(32, 16),
            nn.ReLU(),
            nn.Linear(16, 8)
        )
        
    def forward(self, x):
        logits = self.net(x)
        if self.export:
            return torch.softmax(logits, dim=1)
        return logits
