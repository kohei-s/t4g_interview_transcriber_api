import aiofiles
import asyncio
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
import ffmpeg
import math
import os
from scipy import fromstring, int16
import speech_recognition as sr
import struct
from tempfile import NamedTemporaryFile
import wave

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
    stream = ffmpeg.input(org_file)
    stream = ffmpeg.output(stream, 'audio.wav')
    ffmpeg.run(stream, overwrite_output=True)
    wavf = 'audio.wav'
    return wavf

# sprit wav in parts of 30 sec
def cut_wav(wavf):
    wr = wave.open(wavf, 'r')
    ch = wr.getnchannels()
    width = wr.getsampwidth()
    fr = wr.getframerate()
    fn = wr.getnframes()
    total_time = 1.0 * fn / fr
    integer = math.floor(total_time)
    frames = int(ch * fr * 30)
    num_cut = int(integer // 30)
    data = wr.readframes(wr.getnframes())
    wr.close()
    X = fromstring(data, dtype=int16)

    outf_list = []
    for i in range(num_cut):
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


# endpoints
# define a root '/'
@app.get("/")
def index():
    return {"ok": True}


@app.post("/convert_test/")
async def get_wav_only(file: UploadFile = File(...)):
    try:
        async with aiofiles.tempfile.NamedTemporaryFile("wb",
                                                        delete=False) as temp:
            try:
                contents = await file.read()
                await temp.write(contents)
            except Exception:
                return {"message": "There was an error uploading the file"}
            finally:
                await file.close()

        res = await run_in_threadpool(get_wav, temp.name)
    except Exception:
        return {"message": "There was an error processing the file"}
    finally:
        os.remove(temp.name)

    # use cut_wav func to sprit wav
    cuts = cut_wav(res)

    # convert wav to text
    output_text = ''
    for fwav in cuts:
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

    transcript = {'interview transcript': output_text}
    return transcript
