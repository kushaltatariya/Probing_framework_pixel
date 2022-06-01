import re
import os
import csv
import numpy as np
from enum import Enum
from math import fsum
from pathlib import Path
from typing import Optional, Union, Dict, List, Tuple
from collections import defaultdict
from conllu import parse_tree, parse
from conllu.models import TokenTree, Token
from sklearn.model_selection import train_test_split
from nltk.tokenize import wordpunct_tokenize


class Splitter:
    def __init__(
        self,
        shuffle: bool = True
    ):
        self.shuffle = shuffle


    def read(self, path: str) -> str:
        """
        Reads a file
        Args:
            path: a path to a file
        """
        with open(path, encoding='utf-8') as f:
            conllu_file = f.read()
        return conllu_file 

    def find_category(
        self,
        category: Enum,
        head: Token,
        children: List[TokenTree]
    ) -> Optional[Union[str, Dict]]:
        """
        Finds a token that has a given category and is located on the top of a tree
        Args:
            category: a grammatical value that needed to be found
            head: the root of a sentence
            children: children of a token in token tree
        """
        if head['feats'] and category in head['feats']:
            return head

        for token in children:
            token_info = token.token
            result = self.find_category(category, token_info, token.children)
            if result:
                return result
        return None

    def classify(
        self,
        token_trees: List[TokenTree],
        category: Enum
    ) -> Dict:
        """
        Classifies sentences by a grammatical value they contain
        Args:
            token_trees: sentences represented as trees
            category: a grammatical value
        """
        probing_data = defaultdict(list)
        for token_tree in token_trees:
            s_text = ' '.join(wordpunct_tokenize(token_tree.metadata['text']))
            root = token_tree.token
            category_token = self.find_category(category, root, token_tree.children)
            if category_token:
                value = category_token['feats'][category]
                probing_data[value].append(s_text)
        return probing_data

    def subsamples_split(
        self,
        probing_data: Dict,
        partition: List[float],
        random_seed: int,
        split: List[Enum] = None
    ) -> Dict:
        """
        Splits data into three sets: train, validation, and test
        in the given relation
        Args:
            probing_data: a dictionary that contains grammatical values and
            all the sentences they are found in
            partition: a relation that sentences should be split in
            random_seed: random seed for spliting
            shuffle: if sentences should be randomly shuffled
            split: parts that data should be split to
        """
        data, labels = map(np.array, zip(*probing_data))
        X_train, X_test, y_train, y_test = train_test_split(
            data, labels, stratify=labels, train_size=partition[0],
            shuffle=self.shuffle, random_state=random_seed
        )
        if len(partition) == 2:
            parts = {
                split[0]: [X_train, y_train],
                split[1]: [X_test, y_test]
            }
        else:
            label = [y for y, count in zip(*np.unique(y_test, return_counts=True)) if count > 1]
            X_train = X_train[np.isin(y_train, label)]
            y_train = y_train[np.isin(y_train, label)]
            X_test = X_test[np.isin(y_test, label)]
            y_test = y_test[np.isin(y_test, label)]

            val_size = partition[1] / (1 - partition[0])

            if y_test.size != 0:
                X_val, X_test, y_val, y_test = train_test_split(
                    X_test, y_test, stratify=y_test, train_size=val_size,
                    shuffle=self.shuffle, random_state=random_seed
                )
                parts = {
                    split[0]: [X_train, y_train],
                    split[1]: [X_test, y_test],
                    split[2]: [X_val, y_val]
                }
            else:
                parts = {}
        return parts

    def generate_probing_file(
        self,
        conllu: os.PathLike,
        category: Enum,
        splits: List[Enum] = None,
        partitions: List[float] = [0.8, 0.1, 0.1],
        random_seed: int = 42
    ) -> Dict:
        """
        Generates a split following given arguments
        Args:
            conllu: a string in CONLLU format with the data
            category: a grammatical category to split by
            split: parts that the data are to split to
            partitions: a percentage of splits
            shuffle: if the data should be randomly shuffles
            random_seed: a random seed for spliting
        """
        sentences = parse_tree(conllu)
        classified_sentences = self.classify(sentences, category)
        if len(classified_sentences) == 0:
            parts = {}
        elif fsum(partitions) != 1:
            raise ValueError('the sum of the parts must equal 1')
        elif len(splits) == 1:
            data = {key: value for key, value in classified_sentences.items() if len(value) > 1}
            data = [(v, key) for key, value in data.items() for v in value]
            parts = {splits[0]: list(zip(*data))}
        else:
            data = {key: value for key, value in classified_sentences.items() if len(value) > 1}
            min_value = min([len(value) for value in data.values()], default=0)
            if data and min_value > len(data.keys()) and len(data.keys()) > 1:
                data = [(v, key) for key, value in data.items() for v in value]
                parts = self.subsamples_split(
                    data, partitions,
                    random_seed, splits
                )
            else:
                if len(data.keys()) == 1:
                    print(f"Category {category} has one value")
                parts = {}
        return parts

    def writer(self, result_path: os.PathLike, partition_sets: Dict):
        """
        Writes to a file
        Args:
             result_path: a filename that will be generated
             partition_sets: the data split into 3 parts
        """
        print(f'Writing to file: {result_path}\n')
        with open(result_path, 'w', encoding='utf-8') as newf:
            my_writer = csv.writer(newf, delimiter='\t', lineterminator='\n')
            for part in partition_sets:
                for sentence, value in zip(*partition_sets[part]):
                    my_writer.writerow([part, value, sentence])
        return None

    def check(self, parts: Dict, category: Enum):
        """
        Checks if the data are not empty and have a train set
        Args:
            parts: train, val and test sets
            category: a grammatical value
        """
        if not all(parts.values()):
            print(f'One of the files does not contain examples for {category} \n')
        elif 'tr' in parts and 'va' in parts and 'te' in parts:
            if set(parts['tr'][1]) != set(parts['va'][1]):
                print("The number of category meanings is different in train and validation parts.")
            elif set(parts['tr'][1]) != set(parts['te'][1]):
                print("The number of category meanings is different in train and test parts.")
            save_path_file = Path(self.save_path_dir.absolute(), f'{self.language}{category}.csv')
            self.writer(save_path_file, parts)
        else:
            print(f'There are no examples for {category} in this language \n')
        return None
    
    def find_categories(self, filename):
        set_of_values = set()
        token_lists = parse(filename)
        for token_list in token_lists:
            for token in token_list:
                feats = token['feats']
                if feats:
                    set_of_values.update(feats.keys())
        return sorted(set_of_values)
    
    def get_filepaths_from_dir(self, dir_path: os.PathLike) -> List[os.PathLike]:        
        def sorting_parts_func(p: os.PathLike) -> int:
            p = str(p)
            if 'train' in p:
                return 0
            elif 'dev' in p:
                return 1
            return 2

        filepaths = [Path(dir_path, p) for p in os.listdir(dir_path) if \
                re.match(".*-(train|dev|test).*\.conllu", p)]
        return sorted(filepaths, key=sorting_parts_func)

    def __extract_lang_from_udfile(self, ud_file_path: Path, language: str) -> str:
        if not language:
            return ud_file_path.stem.split('-')[0] + "_"
        return language
    
    def __determine_ud_savepath(self, path_from_files: os.PathLike, save_path_dir: os.PathLike):
        final_path = None
        if not save_path_dir:
            final_path = path_from_files
        else:
            final_path = save_path_dir
        os.makedirs(final_path, exist_ok=True)
        return Path(final_path)

    def generate_(
        self,
        paths: List[os.PathLike],
        splits: List[Enum] = None,
        partitions: List[float] = None
    ) -> None:
        """
        Generates files for all categories
        Args:
            paths: files with data in CONLLU format
            splits: the way how the data should be split
            portions: the percentage of different splits
        """
        texts = [self.read(p) for p in paths]
        categories = self.find_categories("\n".join(texts))
        if len(categories) == 0:
            print(f"Something went wrong during processing paths:")
            print(*paths, sep = '\n')

        for category in categories:
            parts = {}
            for text, split, portion in zip(texts, splits, partitions):
                part = self.generate_probing_file(
                    conllu=text, splits=split,
                    partitions=portion, category=category
                )
                parts.update(part)
            self.check(parts, category)

    def convert(
        self,
        tr_path: Optional[os.PathLike] = None,
        va_path: Optional[os.PathLike] = None,
        te_path: Optional[os.PathLike] = None,
        dir_conllu_path: Optional[os.PathLike] = None,
        language: str = None,
        save_path_dir: Optional[os.PathLike] = None
    ) -> None:
        """
        Converts files in CONLLU format to SentEval probing files
        Args:
            tr_path: a path to a file with all data OR train data
            te_path: a path to a file with test data
            va_path: a path to a file with test data
            dir_path: a path to a directory with all files
        """
        dir_conllu_path = Path(dir_conllu_path).absolute()
        if dir_conllu_path is None:
            known_paths = [Path(p) for p in [tr_path, va_path, te_path] if p is not None]
            assert len(known_paths) > 0
            assert tr_path is not None, "At least path to train data should be passed."
            self.language = self.__extract_lang_from_udfile(known_paths[0], language)
            self.save_path_dir = self.__determine_ud_savepath(known_paths[0].parent, save_path_dir)

            if len(known_paths) == 1:
                self.generate_(
                    [tr_path],
                    (["tr", "va", "te"], ),
                    ([0.8, 0.1, 0.1], )
                )
            elif len(known_paths) == 2:
                second_path = te_path if te_path is not None else va_path
                self.generate_(
                    [tr_path, second_path],
                    (["tr"], ["va", "te"], ),
                    ([1.0], [0.5, 0.5], )
                )
            elif len(known_paths) == 3:
                self.generate_(
                    [tr_path, va_path, te_path],
                    (["tr"], ["va"], ["te"], ),
                    ([1.0], [1.0], [1.0],)
                )
            else:
                raise NotImplementedError(f"Too much files. You provided {len(known_paths)} files")
        else:
            paths = [Path(p) for p in self.get_filepaths_from_dir(dir_conllu_path)]
            assert len(paths) > 0, f"Empty folder: {dir_conllu_path}"

            self.language = self.__extract_lang_from_udfile(paths[0], language)
            self.save_path_dir = self.__determine_ud_savepath(dir_conllu_path, save_path_dir)

            assert len(paths) <= 3, f"Too much files. You provided {len(paths)} files"
            return self.convert(*paths, language = self.language, save_path_dir = self.save_path_dir)
