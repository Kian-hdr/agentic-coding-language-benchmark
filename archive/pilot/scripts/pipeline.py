"""Complete each isolated trial without overlapping writers to a run folder."""
import concurrent.futures
import json
import os
from pathlib import Path
import threading
import time

from benchmark_runner import ROOT, phase
from evaluate import evaluate

LANGUAGES=['python','typescript','go','rust','swift','kotlin','moonbit','baml','zero']
MODEL_SLOTS=threading.Semaphore(3)
EVAL_SLOT=threading.Semaphore(1)

def alive(path):
    try:
        os.kill(int(path.read_text()),0)
        return True
    except (OSError,ValueError,FileNotFoundError): return False

def trial(language,n):
    work=ROOT/'runs'/f'{language}_{n}'
    for name in ['initial','extension']:
        receipt=work/f'{name}_metrics.json'
        while not receipt.exists() and alive(work/f'{name}_pid.txt'):
            time.sleep(2)
        if not receipt.exists():
            with MODEL_SLOTS:
                phase(language,n,name)
        evaluation=ROOT/'results'/f'{language}_{n}_{name}_evaluation.json'
        if not evaluation.exists():
            with EVAL_SLOT:
                evaluate(language,n,name)
    print(json.dumps({'completed':language,'trial':n}),flush=True)

if __name__=='__main__':
    # Existing trial-one jobs were dispatched during toolchain preparation.
    with concurrent.futures.ThreadPoolExecutor(max_workers=9) as pool:
        for f in concurrent.futures.as_completed([pool.submit(trial,l,1) for l in LANGUAGES]):
            f.result()
    (ROOT/'results'/'trial_1_complete').write_text('complete\n')
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for f in concurrent.futures.as_completed([pool.submit(trial,l,2) for l in LANGUAGES]):
            f.result()
    (ROOT/'results'/'all_trials_complete').write_text('complete\n')
