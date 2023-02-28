# list_transcriber
Transcribe a list of files audio files using intelektika.lt transcription service
API: https://app.swaggerhub.com/apis/aireno/Transkipcija

## Running

### prepare env

```bash
conda create --name list python=3.10
conda activate list
pip install -r requirements.txt
```

### configure

Create Makefile.options. Sample:

```Makefile
# zip with audio
data_in?=data/audio.zip
# directory of audio files in the zip
extr_dir?=out
# working dir
work_dir?=out/ms_v1
# number of parallel workers
workers?=10
# key secret
key?=
```

### run transcription

```bash
make build
```

## result

The script prepares transcriptions at `${work_dir}/trans.zip`
```

