import streamlit as st
import numpy as np
import librosa
import joblib
import tensorflow as tf
import keras
import os
import soundfile as sf
import tempfile

# --------------------------------- PARTE 1: EXTRAIR FEATURES --------------------------------- #

# Carregar o modelo e o scaler
MODEL_PATH = "data/models/audio_emotion_model.keras"  # Example
SCALER_PATH = "data/models/scaler.pkl"               # Example

model = keras.models.load_model(MODEL_PATH)
scaler = joblib.load(SCALER_PATH)

# Lista de emoções
EMOTIONS = ["angry", "calm", "disgust", "fear",
            "happy", "neutral", "sad", "surprise"]


# Função para extrair features
def extract_features(audio_path):
    data, sample_rate = librosa.load(audio_path, sr=16000, mono=True)
    features = []

    # Zero Crossing Rate
    # Extract the zcr here
    # features.extend(zcr)
    zcr = librosa.feature.zero_crossing_rate(data)
    zcr_mean = np.mean(zcr, axis=1)
    features.extend(zcr_mean)

    # Chroma STFT
    # Extract the chroma stft here
    # features.extend(chroma)
    chroma_stft = librosa.feature.chroma_stft(y=data, sr=sample_rate)
    chroma_stft_mean = np.mean(chroma_stft, axis=1)
    features.extend(chroma_stft_mean)
    
    # MFCCs
    # Extract the mfccs here
    # features.extend(mfccs)
    mfcc = librosa.feature.mfcc(y=data, sr=sample_rate, n_mfcc=13)
    mfcc_mean = np.mean(mfcc, axis=1)
    features.extend(mfcc_mean)

    # RMS
    # Extract the rms here
    # features.extend(rms)
    rms = librosa.feature.rms(y=data)
    rms_mean = np.mean(rms, axis=1)
    features.extend(rms_mean)

    # Mel Spectrogram
    # Extract the mel here
    # features.extend(mel)
    mel = librosa.feature.melspectrogram(y=data, sr=sample_rate, n_mels=128)
    mel = librosa.power_to_db(mel, ref=np.max)
    mel_mean = np.mean(mel, axis=1)
    features.extend(mel_mean)

    # Garantir que tenha exatamente 155 features (ou truncar/zerar)
    target_length = 155
    if len(features) < target_length:
        features.extend([0] * (target_length - len(features)))
    elif len(features) > target_length:
        features = features[:target_length]

    return np.array(features).reshape(1, -1)


# --------------------------------- PARTE 2: STREAMLIT --------------------------------- #

# Configuração do app Streamlit (Título e descrição)
st.title("🎵 Detector de emoções em aúdio")
st.header("Envie um arquivo de aúdio para análise")

# Upload de arquivo de áudio (wav, mp3, ogg)
uploaded_file = st.file_uploader(
    "Escolha um arquivo de áudio...", type=["wav", "mp3", "ogg"])

if uploaded_file is not None:
    # Salvar temporariamente o áudio

    file_extension = os.path.splitext(uploaded_file.name)[1]
    
    audio_data = uploaded_file.read()

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=file_extension)
    
    temp_file.write(audio_data)
    temp_file.close()  
    
    temp_audio_path = temp_file.name

    # Reproduzir o áudio enviado
    st.audio(audio_data)

    # Extrair features
    features = extract_features(temp_audio_path)

    # Normalizar os dados com o scaler treinado
    features_scaled = scaler.transform(features)

    # Ajustar formato para o modelo
    #features_final = features_scaled
    #st.write(f"Shape das features: {features_final.shape}")
    #Ao usar essas funções eu vi que o formato das features já estão certos, sendo (1, 155)

    # Fazer a predição
    #Por algum motivo no meu código está aparecendo que tem um erro no predict, mas mesmo assim o código está funcionando normalmente
    prediction = model.predict(features_scaled)

    # Tradução dos sentimentos para português
    EMOTIONS = ["angry", "calm", "disgust", "fear",
                "happy", "neutral", "sad", "surprise"]

    EMOTIONS_PT = {
        "angry": "Raiva",
        "calm": "Calma", 
        "disgust": "Nojo",
        "fear": "Medo",
        "happy": "Felicidade",
        "neutral": "Neutro",
        "sad": "Tristeza",
        "surprise": "Surpresa"
}
    # Exibir o resultado
    predicted_emotion_index = np.argmax(prediction)
    predicted_emotion = EMOTIONS[predicted_emotion_index]
    confidence = prediction[0][predicted_emotion_index]

    st.success(f"**Emoção detectada:** {predicted_emotion}")
    st.info(f"**Confiança:** {confidence:.2%}")

    # Exibir probabilidades (gráfico de barras)
    st.subheader("Probabilidades por emoção:")
    prob_dict = {EMOTIONS[i]: prediction[0][i] for i in range(len(EMOTIONS))}
    st.bar_chart(prob_dict)

    # Remover o arquivo temporário
    os.unlink(temp_audio_path)