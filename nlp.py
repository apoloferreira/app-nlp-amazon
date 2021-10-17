
import nltk
import spacy
import re
import string
import pandas as pd
from collections import Counter
from textblob import TextBlob
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from nltk import word_tokenize

nlp = spacy.load('pt_core_news_sm')


# Função para obter subjetividade
def getSubjectivity(text):
    return TextBlob(text).sentiment.subjectivity


# Função para obter polaridade
def getPolarity(text):
    return TextBlob(text).sentiment.polarity


def analise_sentimento(df):
    # Adicionando ao dataframe
    df['Subjectivity'] = df['reviews_en'].apply(getSubjectivity)
    df['Polarity'] = df['reviews_en'].apply(getPolarity)
    
    # Criando um analisador de sentimento
    analisador = SentimentIntensityAnalyzer()
    df['Compound'] = [analisador.polarity_scores(v)['compound'] for v in df['reviews_en']]
    df['Negative'] = [analisador.polarity_scores(v)['neg'] for v in df['reviews_en']]
    df['Neutral']  = [analisador.polarity_scores(v)['neu'] for v in df['reviews_en']]
    df['Positive'] = [analisador.polarity_scores(v)['pos'] for v in df['reviews_en']]
    return df


def tokenizacao(df):
    #nlp = spacy.load('pt_core_news_sm')
    # Tokenizando coluna reviews_pt
    df['tokenization'] = df['reviews_pt'].apply(lambda x: x.split())
    return df


# Função para limpar e lematizar os comentários
def limpa_comentarios(text):
    #nlp = spacy.load('pt_core_news_sm')   
    # Remove pontuação usando expressão regular
    regex = re.compile('[' + re.escape(string.punctuation) + '\\r\\t\\n]')
    nopunct = regex.sub(" ", str(text))    
    # Usa o SpaCy para lematização
    doc = nlp(nopunct, disable = ['parser', 'ner'])
    lemma = [token.lemma_ for token in doc]
    return lemma


def lematizacao(df):
    # Aplica a função aos dados
    df['lemmatized'] = df['reviews_pt'].map(limpa_comentarios)
    return df


def juntar_comentarios(df):
    todos_comentarios_pt = ' '.join([str(palavra) for palavra in df['reviews_pt'].values])
    #todos_comentarios_pt = todos_comentarios_pt.split()
    return todos_comentarios_pt, todos_comentarios_pt.split()


'''
def removendo_stopwords(df, comentarios_pt):
    # Removendo stopwords dos comentários tokenizados em português
    stop_words_pt = set(stopwords.words('portuguese'))
    df['tokenization'] = df['tokenization'].apply(lambda x: [palavra for palavra in x if palavra not in stop_words_pt])
    # Removendo stopwords da lista com todos comentários pt
    comentarios_pt = [palavra for palavra in comentarios_pt if palavra not in stop_words_pt]
    return df, comentarios_pt
'''


# Verifica quais palavras mais utilizadas nos comentários pt
def palavras_mais_usadas(comentarios_pt):
    counter = Counter(comentarios_pt)
    df_counter = pd.DataFrame.from_dict(Counter(comentarios_pt), orient='index').reset_index()
    df_counter.columns = ['palavras', 'freq']
    df_counter.sort_values(by='freq', ascending=False, inplace=True)
    df_counter.reset_index(drop=True, inplace=True)    
    return df_counter.head(10)


# Retorna os brigramas mais usados nos comentários pt
def bigramas(comentarios_pt):
    # Métricas de associação de bigramas (esse objeto possui diversos atributos, como freq, pmi, teste t, etc...)
    bigramas = nltk.collocations.BigramAssocMeasures()
    # O próximo passo é criar um buscador de bigramas nos tokens
    buscaBigramas = nltk.collocations.BigramCollocationFinder.from_words(comentarios_pt)
    # Vamos contar quantas vezes cada bigrama aparece nos tokens dos comentários
    bigrama_freq = buscaBigramas.ngram_fd.items()
    # Vamos converter o dicionário anterior em uma tabela de frequência no formato do Pandas para os bigramas
    FreqTabBigramas = pd.DataFrame(list(bigrama_freq), columns = ['Bigrama', 'Frequencia']).sort_values(by = 'Frequencia', ascending = False)
    FreqTabBigramas['Bigrama'] = FreqTabBigramas['Bigrama'].apply(lambda x: list(x))
    FreqTabBigramas.set_index('Bigrama', inplace=True)
    return FreqTabBigramas.head(10)

