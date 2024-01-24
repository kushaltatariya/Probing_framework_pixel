import os
from typing import Optional
from probing.ud_parser.ud_parser import ConlluUDParser
from glob import glob
from tqdm import tqdm
import re
import shutil

def parse(
    tr_path: Optional[os.PathLike] = None,
    va_path: Optional[os.PathLike] = None,
    te_path: Optional[os.PathLike] = None,
    dir_conllu_path: Optional[os.PathLike] = None,
    language: Optional[str] = None,
    save_path_dir: Optional[os.PathLike] = None,
    shuffle: bool = True,
    verbose: bool = False,
) -> None:
    converter = ConlluUDParser(shuffle, verbose)
    converter.convert(
        tr_path, va_path, te_path, dir_conllu_path, language, save_path_dir
    )

language_re = re.compile(r'UD_(.+)-')


# ud_folders = glob("UD_")
ud_folders = ["UD_Hindi-HDTB", "UD_Tamil-TTB"]
####CREATE THE DATASETS

for folder in tqdm(ud_folders):
    print("Parsing: " + folder)
    parse(dir_conllu_path=folder)

####COPY THE DATASETS TO THE PROBING FOLDER

for folder in tqdm(ud_folders):
    probes = glob(folder + "/*.txt")
    language = language_re.findall(folder)[0]
    print("Copying: " + language)
    parent_dir = "/home/kushal/SentEval/data/probing/"
    new_dir = parent_dir + language
    if not os.path.exists(parent_dir + language):
        os.mkdir(parent_dir + language)
    for probe in tqdm(probes):
        print(probe)
        shutil.copy(probe, new_dir)

senteval_dir = "/home/kushal/SentEval/data/probing/"
task_re = re.compile(r'[A-Za-z]+\.txt$')
languages = [language_re.findall(folder)[0] for folder in ud_folders]

#####RENAME THE FILES

for lang in languages:
    folder = senteval_dir + lang
    probes = glob(folder + "/*.txt")
    for probe in probes:
        task = task_re.findall(probe)[0]
        new_name = folder + '/' + task
        os.rename(probe, new_name)








