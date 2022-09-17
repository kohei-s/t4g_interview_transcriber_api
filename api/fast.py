from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
#from fastapi.concurrency import run_in_threadpool

import json
import os
import ffmpeg
import shutil
import speech_recognition as sr
import wave
import math
import struct
from scipy import fromstring, int16
from tempfile import NamedTemporaryFile
#import aiofiles
#import asyncio

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# functions
# convert mp4 to wav
def get_wav(org_file):
    #if org_file.endwith('.wav'):
    #wavf = org_file
    #else:
    stream = ffmpeg.input(org_file)
    stream = ffmpeg.output(stream, 'audio.wav')
    ffmpeg.run(stream, overwrite_output=True)
    wavf = 'audio.wav'

    return wavf


# sprit wav in parts of 30 sec
def cut_wav(wavf):
    time = 30
    wr = wave.open(wavf, 'r')
    ch = wr.getnchannels()
    width = wr.getsampwidth()
    fr = wr.getframerate()
    fn = wr.getnframes()
    total_time = 1.0 * fn / fr
    integer = math.floor(total_time)
    t = int(time)
    frames = int(ch * fr * t)
    num_cut = int(integer // t)
    data = wr.readframes(wr.getnframes())
    wr.close()
    X = fromstring(data, dtype=int16)

    outf_list = []
    for i in range(num_cut):
        #output_dir = 'output/cut_wav/'
        #outf = 'output/' + str(i) + '.wav'
        outf = str(i) + '.wav'
        start_cut = i * frames
        end_cut = i * frames + frames
        Y = X[start_cut:end_cut]
        outd = struct.pack("h" * len(Y), *Y)
        ww = wave.open(outf, 'w')
        ww.setnchannels(ch)
        ww.setsampwidth(width)
        ww.setframerate(fr)
        ww.writeframes(outd)
        ww.close()
        outf_list.append(outf)

    os.remove(wavf)
    return outf_list


# convert wav to text
def get_transcript(outf_list):
    output_text = ""
    #audio_num = len(outf_list)

    for fwav in outf_list:
        try:
            r = sr.Recognizer()
            with sr.AudioFile(fwav) as source:
                audio = r.record(source)
            text = r.recognize_google(audio, language='de-DE')
            output_text = output_text + text + '\n'
            os.remove(fwav)

        except sr.UnknownValueError:
            message = "Could not understand audio"
            output_text = output_text + message + '\n'
            os.remove(fwav)

    return output_text


# endpoints
# define a root '/'
@app.get("/")
def index():
    return {"ok": True}


@app.post("/convert_test/")
def get_wav_only(file: UploadFile = File(...)):
    temp = NamedTemporaryFile(delete=False)
    try:
        try:
            contents = file.file.read()
            with temp as f:
                f.write(contents)
        except Exception:
            return {"message": "There was an error uploading the file"}
        finally:
            file.file.close()

        res = get_wav(temp.name)  # Pass temp.name to VideoCapture()
    except Exception:
        return {"message": "There was an error processing the file"}
    finally:
        #temp.close()  # the `with` statement above takes care of closing the file
        os.remove(temp.name)


    cuts = cut_wav(res)

    text = get_transcript(cuts)

    my_dict = {'interview transcript': text}
    transcript = json.dumps(my_dict)

    return transcript



@app.get("/cut_test")
def cut_wav_only(file):
    wavf = get_wav_only(file)
    cuts = cut_wav(wavf)
    return cuts


@app.get("/transcribe_test")
def get_transcript(file):
    wavf = get_wav_only(file)
    cuts = cut_wav(wavf)
    text = get_transcript(cuts)
    return {'interview transcript': text}
