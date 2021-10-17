
# Imports
import streamlit as st
import streamlit.components.v1 as stc
from PIL import Image
import matplotlib.pyplot as plt
import plotly.express as px
import seaborn as sns
import pandas as pd
import requests
import re
import time
import unicodedata
from collections import Counter
from bs4 import BeautifulSoup
from googletrans import Translator
from wordcloud import WordCloud
from nltk.corpus import stopwords
import nlp

# Stopwords
stop_words_pt = set(stopwords.words('portuguese'))


#### Configurações do Layout ####


st.set_page_config(
    page_title="Amazon Reviews", 
    page_icon=":trophy:", 
    layout="centered")

# Importando arquivo css
with open("styles/style.css") as f:
    st.markdown(f'<style>{f.read()}</style>',unsafe_allow_html=True)

html_banner = """
    <div style="background-color:#F2F4F4;padding:10px;border-radius:10px">
    <h1 style="color:{};text-align:center;">{}%</h1>
    """


##### Programando Parte Superior da Aplicação Web #####


# Imagem
amazon_logo = Image.open('images/amazon_logo.png')
st.image(amazon_logo, caption=None, width=None)

st.title("**Análise de Comentários de Produtos na Amazon**")
st.markdown('-----')
st.markdown("#### :crystal_ball: Veja de forma resumida o sentimento geral dos comentários de um produto e ainda as palavras mais utilizadas</h5>",  unsafe_allow_html=True)
url = st.text_input("Cole abaixo o link do produto:")


##### Programando Funções da Aplicação Web #####


# Busca o nome do produto conforme aparece na url
def obter_produto(resultado):
    soup = BeautifulSoup(resultado, 'lxml')
    link_pagina = soup.find("a", class_="a-link-emphasis a-text-bold", href=True)    
    produto = link_pagina['href'][1:]    
    produto = re.findall(r'[^/]+', produto, flags=re.I)
    return produto[0]

# Busca nome e imagem do produto conforme anuncio da página
def obter_nome_imagem_produto(resultado):
    soup = BeautifulSoup(resultado, 'html.parser')
    nome_produto = soup.find("span", {'id':"productTitle"}, text=True).get_text()
    nome_produto = re.sub('\n+', '', nome_produto)    
    imagem = soup.find("div", class_="imgTagWrapper")
    imagem = imagem.find('img')    
    return nome_produto, imagem['src']

# Conecta a url para fazer verificação
def testar_url(url):
    tentativas = 30
    saida = False
    for tentativa in range(tentativas):
        resultado = requests.get(url)
        if resultado.status_code == 200:
            saida = True
            break
        time.sleep(2)
    return saida, resultado.text

# Obtêm o nome do produto conforme url e anúncio e o código
def estratificar_link(url):
    produto = ""
    codigo = ""
    nome_produto = ""
    src_imagem = ""
    status_url, resultado = testar_url(url)
    if status_url:
        nome_produto, src_imagem = obter_nome_imagem_produto(resultado)
    if url[:29] == "https://www.amazon.com.br/dp/":        
        codigo = re.findall(url[:29] + r'[a-zA-Z0-9]+', url, flags=re.I)
        codigo = codigo[0][29:]
        status_url, resultado = testar_url(url)
        if status_url:
            produto = obter_produto(resultado)
    else:
        produto = re.findall(r'https://www.amazon.com.br/[a-zA-Z0-9%-]+', url, flags=re.I)
        url_temp = produto[0] + '/dp/'
        produto = produto[0][26:]
        codigo = re.findall(url_temp + r'[a-zA-Z0-9]+', url, flags=re.I)
        tamanho_url = 26 + len(produto) + 4
        codigo = codigo[0][tamanho_url:]
    return produto, codigo, nome_produto, src_imagem

# Obtendo comentários do produto
def obter_comentarios(resultado):
    soup = BeautifulSoup(resultado, 'lxml')
    comentarios_web = soup.find_all("a", class_="a-size-base a-link-normal review-title a-color-base review-title-content a-text-bold")    
    return comentarios_web

# Retorna link da páginas de comentários e comentários
def search_reviews(produto, codigo):
    urls = []
    pag = 2
    comentarios_web = []
    
    url_first = f"https://www.amazon.com.br/{produto}/product-reviews/{codigo}/ref=cm_cr_dp_d_show_all_btm?ie=UTF8&reviewerType=all_reviews"
    status_url, resultado = testar_url(url_first)
    
    if status_url:
        urls.append(url_first)
        comentarios_web += obter_comentarios(resultado)        
        while True:
            url_next = f"https://www.amazon.com.br/{produto}/product-reviews/{codigo}/ref=cm_cr_getr_d_paging_btm_next_{pag}?pageNumber={pag}"
            status_url, resultado = testar_url(url_next)
            if status_url:
                comentarios_temp = obter_comentarios(resultado)
                if len(comentarios_temp) == 0:
                    break
                else:
                    urls.append(url_next)
                    comentarios_web += comentarios_temp
                    pag += 1
    else:
        print(f"Obteve status {status_url}, verifique o LINK do produto!")
    return urls, comentarios_web

# Função para remover caracteres non-ascii
def removeNoAscii(s):
    return "".join(i for i in s if ord(i) < 128)

# Tratamento dos comentários
def tratamento_dados(comentarios):
    # Criando Series Pandas com a lista de comentários
    pd_comentarios = pd.Series(comentarios)
    # Removendo valores nulos
    pd_comentarios.dropna(inplace=True)
    # Removendo acenturação
    pd_comentarios = pd_comentarios.apply(lambda x: ''.join(ch for ch in unicodedata.normalize('NFKD', x) if not unicodedata.combining(ch)))
    # Removendo caracteres especiais
    pd_comentarios.replace("[^a-zA-Z,.!?]", " ", regex=True, inplace=True)
    # Remove caracteres non-ascii 
    pd_comentarios = pd_comentarios.map(lambda x: removeNoAscii(x))
    # Definindo todos caracteres como minusculo
    pd_comentarios = pd_comentarios.str.lower()
    # Removendo duplicidades
    pd_comentarios.drop_duplicates(inplace = True)
    # Criando DataFrame com dados tratados
    df_comentarios = pd.DataFrame(pd_comentarios, columns=['reviews_pt'])
    return df_comentarios

# Tradução dos comentários de português para inglês
def traduzir(df):
    translator = Translator()
    df['reviews_en'] = df['reviews_pt'].apply(lambda x: translator.translate(x, src="pt", dest="en").text)
    # Removendo caracteres de pontuação
    df['reviews_pt'].replace("[^a-zA-Z]", " ", regex=True, inplace=True)
    df['reviews_en'].replace("[^a-zA-Z]", " ", regex=True, inplace=True)
    return df

# Gera dados para serem plotanos no gráfico de pizza
def pie_data(df):
    df_pie = df.mean()
    df_pie = df_pie.reset_index()
    df_pie.columns = ['sentiment', 'porcent']
    df_pie = df_pie.query("sentiment == 'Positive' or sentiment == 'Neutral' or sentiment == 'Negative'")
    return df_pie

def texto_final():
    st.markdown("<h5 style='font-weight:bolder;text-align:center;'>Tools</h5>", unsafe_allow_html=True)
    st.markdown("- **Programming language**: Python", unsafe_allow_html=True)
    st.markdown("- **Deploy**: Streamlit", unsafe_allow_html=True)
    st.markdown("- **Hosting**: Heroku", unsafe_allow_html=True)
    st.markdown("<h5 style='font-weight:bolder;text-align:center;'>Techniques</h5>", unsafe_allow_html=True)
    st.markdown("- Web Scraping", unsafe_allow_html=True)
    st.markdown("- Natural Language Processing", unsafe_allow_html=True)
    st.markdown("<h5 style='font-weight:bolder;text-align:center;'>GitHub</h5>", unsafe_allow_html=True)
    st.markdown("* [apoloferreira](https://github.com/apoloferreira)", unsafe_allow_html=True)


##### Programando o Botão de Ação da Aplicação #####


if(st.button("Pesquisar")):

    # Mensagem temporária
    with st.spinner('Verificando página...'):
        time.sleep(8)

    # Pegar o nome e código do produto por meio do link
    produto, codigo, nome_produto, src_imagem = estratificar_link(url)

    # Verificar se consegiui extrair o nome do produto
    if produto == "":
        st.error("Link Inválido, tente novamente!")
    else:
        # Mensagem fixa
        st.success('Página verificada!')

        # Msostrando nome e imagem do produto
        st.markdown(f"<h5 style='text-align:center; font-size:25px;'>{nome_produto}</h5>", unsafe_allow_html=True)

        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            st.markdown(f"[![Foo]({src_imagem})](http://google.com.br/)")        
        
        # Faz o scraping do conteúdo das paginas e os comentários
        urls, comentarios_web = search_reviews(produto, codigo)

        if not comentarios_web:
            st.warning(":pensive: Desculpe, este produto não contêm comentários!!!")
            st.info("Tente outro produto de seu interesse que tenha comentários")
        else:

            # Mensagem temporária
            with st.spinner('Coletando comentários...'):
                time.sleep(5)

            # Unindo os comentários em uma lista
            comentarios = []
            for cw in comentarios_web:
                comentario = cw.find('span').decode_contents()
                comentarios.append(comentario)
            
            # Mensagem fixa
            st.success("Coletado comentários!")        

            df_comentarios = tratamento_dados(comentarios)        

            # Mensagem temporária
            with st.spinner('Traduzindo comentários para melhor interpretação...'):
                time.sleep(8)
            
            # Traduzindo comentários
            df_comentarios = traduzir(df_comentarios)

            # Realiza a análise de sentimento dos comentários em inglês
            df_comentarios = nlp.analise_sentimento(df_comentarios)

            # Tokeniza os comentários
            df_comentarios = nlp.tokenizacao(df_comentarios)

            # Não esta sendo usado
            #df_comentarios = nlp.lematizacao(df_comentarios)

            # Agrupa todos comentários em uma lista. Utilizado para contagem das palavras usadas
            str_todos_comentarios, todos_comentarios = nlp.juntar_comentarios(df_comentarios)

            # Removendo Stopwords
            df_comentarios['tokenization'] = df_comentarios['tokenization'].apply(lambda x: [palavra for palavra in x if palavra not in stop_words_pt])
            todos_comentarios = [palavra for palavra in todos_comentarios if palavra not in stop_words_pt]

            # Não esta sendo usado
            #df_comentarios, todos_comentarios_pt = nlp.removendo_stopwords(df_comentarios, todos_comentarios)

            # Gerando DataFrame com as palavras mais usadas e sua freguência
            df_palavras_mais_usadas = nlp.palavras_mais_usadas(todos_comentarios)

            # Gera DataFrame com o bigrama
            df_bigramas = nlp.bigramas(todos_comentarios)

            # Gera os dados para serem plotados
            df_pie = pie_data(df_comentarios)

            # Gráfico de pizza
            pie_chart = px.pie(
                data_frame = df_pie, 
                values = 'porcent', 
                names = 'sentiment', 
                color = 'sentiment',
                hover_name = 'sentiment', 
                labels={"sentiment":"Sentiment"}, 
                template = 'plotly', 
                width = 700,
                height = 500,
                hole = 0.5, 
                title = "Classificação dos comentários", 
                color_discrete_map={"Positive":'#54A54B',"Neutral":'rgb(179,179,179)',"Negative":"#E45756"}
            )

            # Plotando gráfico
            st.write(pie_chart)

            # Dividindo layout da página em 3 colunas
            col1, col2, col3 = st.columns(3)

            with col1:
                stc.html(html_banner.format("#54A54B", round(df_comentarios.Positive.mean()*100, 1)))
            with col2:
                stc.html(html_banner.format("#17202A", round(df_comentarios.Neutral.mean()*100, 1)))
            with col3:
                stc.html(html_banner.format("#E45756", round(df_comentarios.Negative.mean()*100, 1)))
            
            #col1.markdown(f"<h5 style='font-weight:bolder;text-align:center;color:#54A54B; font-size:40px;'>{round(df_comentarios.Positive.mean()*100, 1)}%</h5>", unsafe_allow_html=True)
            #col2.markdown(f"<h5 style='font-weight:bolder;text-align:center;color:rgb(179,179,179); font-size:40px;'>{round(df_comentarios.Neutral.mean()*100, 1)}%</h5>", unsafe_allow_html=True)
            #col3.markdown(f"<h5 style='font-weight:bolder;text-align:center;color:#E45756; font-size:40px;'>{round(df_comentarios.Negative.mean()*100, 1)}%</h5>", unsafe_allow_html=True)

            st.markdown("<h2 style='text-align:center;'>Palavras mais encontradas</h2>", unsafe_allow_html=True)

            # Gerando gráfico de palavras mais usadas nos comentários
            wordcloud = WordCloud(background_color='white', width=900, height=400, stopwords=stop_words_pt)
            wordcloud.generate(str_todos_comentarios)

            # Plotando gráfico
            fig, ax = plt.subplots(figsize=(20,8))
            ax.imshow(wordcloud, interpolation='bilinear')
            ax.set_axis_off()
            st.pyplot(fig)

            st.markdown("<p></p>", unsafe_allow_html=True)

            col4, col5 = st.columns(2)

            # Plotando gráfico de barras para as palavras mais utilizadas individualmente
            with col4:
                st.markdown("<h5 style='text-align:center;'>Monograma</h5>", unsafe_allow_html=True)
                fig, ax = plt.subplots(figsize=(6,8))

                ax.barh(df_palavras_mais_usadas['palavras'].head(10), df_palavras_mais_usadas['freq'].head(10))
                plt.tight_layout()
                ax.xaxis.grid(linestyle = '--', linewidth = 0.3)
                #title = plt.title("Uma Palavra", pad=20, fontsize=25)

                sns.barplot(x='freq', y='palavras', data=df_palavras_mais_usadas.head(10), palette='mako')

                ax.set_xlabel("Frequência", fontsize=16)
                ax.set_ylabel("")

                ax.set_xticklabels(ax.get_xticklabels(), 
                                horizontalalignment = 'center', 
                                fontsize=12)

                ax.set_yticklabels(ax.get_yticklabels(), 
                                horizontalalignment = 'right', 
                                fontsize=14, 
                                fontweight='bold')

                for py, px in enumerate(df_palavras_mais_usadas.freq):
                    ax.annotate("{:,}".format(px), xy=(px-0.6,py), va='center', bbox=dict(fc='#f0f0f0'))
                plt.show()            
                st.pyplot(fig)

            with col5:
                st.markdown("<h5 style='text-align:center;'>Bigrama</h5>", unsafe_allow_html=True)
                st.dataframe(df_bigramas.head(9))
        
        st.markdown("<p></p>", unsafe_allow_html=True)
        st.markdown("<p></p>", unsafe_allow_html=True)
        st.markdown('-----')
        st.markdown("<p></p>", unsafe_allow_html=True)
        st.markdown("<p></p>", unsafe_allow_html=True)

        # Rodapé da página
        my_expander = st.expander("Como foi desenvolvido??", expanded=False)
        with my_expander:
            clicked = texto_final()
    

