"""Entry point"""
import sys

# from analyzer import normalize, read_file, word_freq, compute_TfIDF
# import summarizer as summarize
import src.util.analyzer as az
import src.util.summarizer as sz
from src.util import arguments
import pprint

if __name__ == "__main__":
    tm_arguments = arguments.parse(sys.argv[1:])
    directory = tm_arguments.directory
    # TFIDF = normalize(read_file(sys.argv[1]))
    # FREQ = word_freq(read_file(sys.argv[1]))
    # # print(FREQ)
    # compute_TfIDF(TFIDF)u
    # print(summarize("cs100f2019_lab05_reflections"))
    print(az.dir_frequency(directory))
    # print(sz.summarizer("cs100f2019_lab05_reflections"))
    # print(summarize("test_resource"))
