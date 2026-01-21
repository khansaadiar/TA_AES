# TA_AES
Project Tugas Akhir Automated Essay Scoring.

## Setup Instructions

### Backend
1.  Navigate to `backend` directory.
2.  Install dependencies: `pip install -r requirements.txt` (Create requirements.txt if needed)
3.  **IMPORTANT: Model File**
    - The model file `model_prompt_3_qwk_0_7879.pth` is too large for GitHub.
    - Please download `model_prompt_3_qwk_0_7879.zip` from [SOURCE_LINK_HERE] (You verify this).
    - **Extract/Unzip** it.
    - Place the `.pth` file in: `backend/models/model_prompt_3_qwk_0_7879.pth`.
4.  Run the server: `python main.py` or `uvicorn main:app --reload`

### Frontend
1.  Navigate to `frontend`.
2.  `npm install`
3.  `npm run dev`