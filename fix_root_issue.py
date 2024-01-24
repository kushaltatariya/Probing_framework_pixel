import os
from typing import Optional
from ud_parser_edit import ConlluUDParser

def parse(
    tr_path: Optional[os.PathLike] = None,
    va_path: Optional[os.PathLike] = None,
    te_path: Optional[os.PathLike] = None,
    dir_conllu_path: Optional[os.PathLike] = None,
    language: Optional[str] = None,
    save_path_dir: Optional[os.PathLike] = None,
    shuffle: bool = False,
    verbose: bool = False,
) -> None:
    converter = ConlluUDParser(shuffle, verbose)
    converter.convert(
        tr_path, va_path, te_path, dir_conllu_path, language, save_path_dir
    )

folder_path = "UD_English-EWT"

parse(dir_conllu_path=folder_path)
