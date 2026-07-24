from langchain_google_genai import ChatGoogleGenerativeAI,GoogleGenerativeAIEmbeddings
from langchain_huggingface import ChatHuggingFace,HuggingFaceEndpoint
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi,TranscriptsDisabled
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda,RunnablePassthrough,RunnableParallel
import os
load_dotenv()

# llm=HuggingFaceEndpoint(repo_id='mistralai/Mistral-7B-Instruct-v0.3',huggingfacehub_api_token=os.getenv('HUGGINGFACE_ACCESS_TOKEN'),provider="auto")

model=ChatGoogleGenerativeAI(model="gemini-3.5-flash-lite",api_key=os.getenv('GOOGLE_API_KEY'),temperature=0.2)
# llm = HuggingFaceEndpoint(
#     repo_id="Qwen/Qwen2.5-7B-Instruct",
#     provider="featherless-ai",
#     huggingfacehub_api_token=os.getenv("HUGGINGFACE_ACCESS_TOKEN"),
#     task="conversational",
#     temperature=0.2
# )
# model=ChatHuggingFace(llm=llm)
embeddings=GoogleGenerativeAIEmbeddings(model='gemini-embedding-2-preview')
parser=StrOutputParser()
store=Chroma(
    collection_name='project',
    embedding_function=embeddings,
    persist_directory='my_db_chrome'
)

def get_transcript(video_id):
    ytt_api = YouTubeTranscriptApi()
    try:
        transcript = ytt_api.fetch(
            video_id,
            languages=['en']
        )
        transcript_text=" ".join(chunk.text for chunk in transcript)
    except TranscriptsDisabled:
        return ("No transcript found!!")
    return transcript_text

def video_exists(video_id):
    result=store.get(where={'video_id':video_id})
    return len(result['ids'])>0

def create_vectorstore(video_id):
    transcript_text=get_transcript(video_id)
    splitter=RecursiveCharacterTextSplitter(
        chunk_size=5000,
        chunk_overlap=800
    )
    chunks=splitter.create_documents([transcript_text],metadatas=[{"video_id":video_id}])
    store.add_documents(chunks)
    return store

def get_store(video_id):
    if video_exists(video_id):
        return store
    return create_vectorstore(video_id)

def load_video(video_id):
    if video_exists(video_id):
        return get_store(video_id)
    else:
        create_vectorstore(video_id)
    return "Video Loaded successfully"

def ask_video(video_id,question):
    vectorstore=get_store(video_id)
    retriver=vectorstore.as_retriever(search_type="mmr", search_kwargs={'k':5,'fetch_k':20,'lambda_mult':0.3,'filter':{'video_id':{"$eq":video_id}}})
    def format(retrived_docs):
        context='\n\n'.join(doc.page_content for doc in retrived_docs)
        return context

    parallel_chain=RunnableParallel({
        'context':retriver|RunnableLambda(format),
        'question':RunnablePassthrough()
    })

    prompt=PromptTemplate(
        template="""    
            You are a helpful YouTube video assistant.
            Your job is to answer user questions.

            Rules:
            1. If the user is greeting you or asking a general conversational question, answer normally.
            2. If the question is related to the video, use only the provided transcript context.
            3. If a video-related answer is not available in the transcript context, say "I don't know based on this video."
            4. Do not make up information from outside the transcript.
            {context}
            Question:{question}
        """,
        input_variables=['context','question']
    )
    chain=parallel_chain|prompt|model|parser
    response=chain.invoke(question)
    return response
    