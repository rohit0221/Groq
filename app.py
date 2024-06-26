# importing dependencies 
import os
from dotenv import load_dotenv
load_dotenv()
import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain_community.vectorstores import FAISS
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from html_stylesheet import css, bot_template, user_template
from langchain_groq import ChatGroq

# creating custom template to guide llm model
custom_template = """Given the following conversation and a follow up question, rephrase the follow up question to be a standalone question, in its original language.
Chat History:
{chat_history}
Follow Up Input: {question}
Standalone question:"""

CUSTOM_QUESTION_PROMPT = PromptTemplate.from_template(custom_template)

# extracting text from pdf
def get_pdf_text(docs):
    text=""
    for pdf in docs:
        pdf_reader=PdfReader(pdf)
        for page in pdf_reader.pages:
            text+=page.extract_text()
    return text

# converting text to chunks
def get_chunks(raw_text):
    text_splitter=CharacterTextSplitter(separator="\n",
                                        chunk_size=1000,
                                        chunk_overlap=200,
                                        length_function=len)   
    chunks=text_splitter.split_text(raw_text)
    return chunks

# using all-MiniLm embeddings model and faiss to get vectorstore
def get_vectorstore(chunks):
    embeddings=HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2",
                                     model_kwargs={'device':'cpu'})
    vector_store = FAISS.from_texts(chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")
    return vector_store

# generating conversation chain  

def get_conversationchain(vectorstore):
    llm=ChatGroq(model_name="Llama3-70b-8192")
    memory = ConversationBufferMemory(memory_key='chat_history', 
                                      return_messages=True,
                                      output_key='answer') # using conversation buffer memory to hold past information
    conversation_chain = ConversationalRetrievalChain.from_llm(
                                llm=llm,
                                retriever=vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 6}),
                                condense_question_prompt=CUSTOM_QUESTION_PROMPT,
                                memory=memory)
    
    return conversation_chain

# generating response from user queries and displaying them accordingly
def handle_question(question):
    response=st.session_state.conversation({'question': question})
    st.session_state.chat_history=response["chat_history"]
    for i,msg in enumerate(st.session_state.chat_history):
        if i%2==0:
            st.write(user_template.replace("{{MSG}}",msg.content,),unsafe_allow_html=True)
        else:
            st.write(bot_template.replace("{{MSG}}",msg.content),unsafe_allow_html=True)


def main():
    load_dotenv()
    st.set_page_config(page_title="Chat with your PDFs💁🏻‍♀️")
    st.write(css,unsafe_allow_html=True)
    if "conversation" not in st.session_state:
        st.session_state.conversation=None

    if "chat_history" not in st.session_state:
        st.session_state.chat_history=None
    
    st.header("Chat with your PDFs 💁🏻‍♀️")
    question=st.text_input("Ask question from your document:")
    if question:
        handle_question(question)
    with st.sidebar:
        st.subheader("My PDFs")
        docs=st.file_uploader("Upload your PDF files here and click 'Process'",accept_multiple_files=True)
        if st.button("Consume my PDFs"):
            with st.spinner("Processing, hang in there..."):
                
                #get the pdf
                raw_text=get_pdf_text(docs)
                
                #get the text chunks
                text_chunks=get_chunks(raw_text)
                
                #create vectorstore
                vectorstore=get_vectorstore(text_chunks)
                
                #create conversation chain
                st.session_state.conversation=get_conversationchain(vectorstore)


if __name__ == '__main__':
    main()