from src.D_Modelos.Reviews.FASTopic_classifier import spacy_tokenizer
import sys

print("Cambiando path")
sys.modules["spacy_tokenizer"] = spacy_tokenizer
print("Path cambiado")