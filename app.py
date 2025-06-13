import os
import json
import textwrap
import glob
import time
import uuid
from typing import List, Dict, Optional, Any
import numpy as np
import logging

# Import LangChain components
from langchain_community.vectorstores import Chroma
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain_community.embeddings import HuggingFaceHubEmbeddings
from langchain.embeddings import HuggingFaceEmbeddings

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.prompts import PromptTemplate
from langchain_google_genai import GoogleGenerativeAI
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import numpy as np
import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("asha_chatbot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("asha_chatbot")

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define models for API requests and responses
class ChatRequest(BaseModel):
    query: str
    chat_history: List[Dict[str, Any]] = []
    context_type: Optional[str] = "all"

class FeedbackRequest(BaseModel):
    conversation_id: str
    message_id: str
    feedback_type: str  # "helpful", "not_helpful", "reported"
    details: Optional[str] = None

HUGGINGFACE_HUB_API_TOKEN = os.getenv("HUGGINGFACE_HUB_API_TOKEN", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your api")

# Initialize LLM
llm = GoogleGenerativeAI(model="gemini-2.0-flash", api_key=GEMINI_API_KEY)

# Initialize memory
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

def load_documents():
    """Loads PDFs, JSON, and text documents into a list of LangChain Document objects."""
    documents = []

    # Load PDF
    pdf_file = "scheme.pdf"
    if os.path.exists(pdf_file):
        try:
            pdf_loader = PyPDFLoader(pdf_file)
            documents.extend(pdf_loader.load())
            logger.info(f"Loaded {len(documents)} pages from {pdf_file}")
        except Exception as e:
            logger.error(f"Error loading PDF {pdf_file}: {e}")

    # Load JSON Files
    json_files = ["governmentschemes.json", "job_listings.json", "community_events.json", "mentorship_programs.json"]
    
    for json_file in json_files:
        if os.path.exists(json_file):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    json_data = json.load(f)

                if isinstance(json_data, list):
                    for item in json_data:
                        documents.append(Document(page_content=json.dumps(item), metadata={"source": json_file}))
                elif isinstance(json_data, dict):
                    documents.append(Document(page_content=json.dumps(json_data), metadata={"source": json_file}))

                logger.info(f"Loaded data from {json_file}")

            except Exception as e:
                logger.error(f"Error loading JSON {json_file}: {e}")

    # Load Text Files
    txt_files = [
        "dairybusiness.txt",
        "tutoringbusiness.txt",
        "tailoringbusiness.txt",
        "careers_for_women.txt",
        "women_empowerment.txt"
    ]

    # Include all `.txt` files in the current directory
    txt_files.extend([f for f in glob.glob("*.txt") if f not in txt_files])

    for txt_file in txt_files:
        if os.path.exists(txt_file):
            try:
                loader = TextLoader(txt_file, encoding="utf-8")
                documents.extend(loader.load())
                logger.info(f"Loaded text file: {txt_file}")
            except Exception as e:
                logger.error(f"Error loading text file {txt_file}: {e}")

    # Create missing files with sample data
    create_sample_files()
    
    return documents

def create_sample_files():
    """Create sample data files if they don't exist"""
    # Create careers_for_women.txt if it doesn't exist
    career_file = "careers_for_women.txt"
    if not os.path.exists(career_file):
        career_content = """
# Career Opportunities for Women in India

## Technology Careers
- Software Development
- Data Science and Analytics
- Cybersecurity
- UI/UX Design
- Digital Marketing

## Healthcare Careers
- Nursing
- Medical Technicians
- Pharmacists
- Healthcare Administration

## Education Careers
- Teaching (all levels)
- Educational Administration
- Online Education
- Special Education

## Business and Finance
- Accounting
- Financial Analysis
- Banking
- Human Resources
"""
        with open(career_file, "w", encoding="utf-8") as f:
            f.write(career_content)
        logger.info(f"Created sample file: {career_file}")
    
    # Create job_listings.json if it doesn't exist
    job_file = "job_listings.json"
    if not os.path.exists(job_file):
        jobs = [
            {
                "id": "job1",
                "title": "Software Developer",
                "company": "TechWomen Inc.",
                "location": "Bangalore, Remote",
                "description": "Entry-level software development position with flexible hours, ideal for women returning to work.",
                "requirements": "Basic programming skills, willingness to learn",
                "salary": "₹5,00,000 - ₹8,00,000 per annum",
                "apply_link": "https://example.com/apply/job1",
                "posted_date": "2025-04-10",
                "women_friendly_benefits": ["Remote work options", "Flexible hours", "Maternity benefits"]
            },
            {
                "id": "job2",
                "title": "Content Writer",
                "company": "CreativeMinds",
                "location": "Delhi, Hybrid",
                "description": "Content creation role with part-time options available.",
                "requirements": "Good writing skills, creativity",
                "salary": "₹4,00,000 - ₹6,00,000 per annum",
                "apply_link": "https://example.com/apply/job2",
                "posted_date": "2025-04-15",
                "women_friendly_benefits": ["Part-time options", "Work from home days"]
            }
        ]
        with open(job_file, "w", encoding="utf-8") as f:
            json.dump(jobs, f, indent=2)
        logger.info(f"Created sample file: {job_file}")
    
    # Create community_events.json if it doesn't exist
    events_file = "community_events.json"
    if not os.path.exists(events_file):
        events = [
            {
                "id": "event1",
                "title": "Women in Tech Conference",
                "organizer": "TechWomen Association",
                "location": "Bangalore",
                "online": True,
                "date": "2025-05-15",
                "time": "10:00 AM - 4:00 PM",
                "description": "Conference focusing on career opportunities for women in technology",
                "registration_link": "https://example.com/register/event1",
                "is_free": True
            },
            {
                "id": "event2",
                "title": "Resume Building Workshop",
                "organizer": "Career Forward",
                "location": "Delhi",
                "online": False,
                "date": "2025-05-20",
                "time": "2:00 PM - 5:00 PM",
                "description": "Learn how to create an impactful resume that stands out to employers",
                "registration_link": "https://example.com/register/event2",
                "is_free": True
            }
        ]
        with open(events_file, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=2)
        logger.info(f"Created sample file: {events_file}")
    
    # Create mentorship_programs.json if it doesn't exist
    mentorship_file = "mentorship_programs.json"
    if not os.path.exists(mentorship_file):
        mentorships = [
            {
                "id": "mentor1",
                "title": "Tech Career Mentorship",
                "organization": "Women in Tech India",
                "duration": "3 months",
                "format": "Online, 1 hour per week",
                "description": "One-on-one mentorship for women entering the technology field",
                "mentor_expertise": ["Software Development", "Product Management", "Data Science"],
                "application_deadline": "2025-05-30",
                "application_link": "https://example.com/apply/mentor1"
            },
            {
                "id": "mentor2",
                "title": "Women Entrepreneurs Mentorship",
                "organization": "StartUp India Women's Wing",
                "duration": "6 months",
                "format": "Hybrid (online and in-person), 2 hours per week",
                "description": "Guidance for women starting their own businesses",
                "mentor_expertise": ["Business Planning", "Marketing", "Finance", "Operations"],
                "application_deadline": "2025-06-15",
                "application_link": "https://example.com/apply/mentor2"
            }
        ]
        with open(mentorship_file, "w", encoding="utf-8") as f:
            json.dump(mentorships, f, indent=2)
        logger.info(f"Created sample file: {mentorship_file}")
    
    # Create women_empowerment.txt if it doesn't exist
    empowerment_file = "women_empowerment.txt"
    if not os.path.exists(empowerment_file):
        empowerment_content = """
# Women Empowerment Initiatives in India

## Educational Initiatives
- Beti Bachao, Beti Padhao (Save the girl child, educate the girl child)
- National Program for Education of Girls at Elementary Level
- Kasturba Gandhi Balika Vidyalaya (KGBV)

## Financial Empowerment Programs
- Mahila E-Haat (Online marketplace for women entrepreneurs)
- Stand Up India Scheme (Loans for women entrepreneurs)
- Mahila Shakti Kendra (Empowerment through community participation)
- Rashtriya Mahila Kosh (National Credit Fund for Women)
- MUDRA Scheme (Small loans for micro-enterprises)
"""
        with open(empowerment_file, "w", encoding="utf-8") as f:
            f.write(empowerment_content)
        logger.info(f"Created sample file: {empowerment_file}")

def get_vector_db(documents=None):
    # Initialize embedding model
   
    
    embeddings = HuggingFaceHubEmbeddings(
    huggingfacehub_api_token="your_huggingface_api_token_here",  # Remove the actual token here
    repo_id="sentence-transformers/all-MiniLM-L6-v2",
    task="feature-extraction"
    )

    
    persist_directory = "chroma_db"
    
    # Check if the vector database already exists
    if os.path.exists(persist_directory) and os.path.isdir(persist_directory) and len(os.listdir(persist_directory)) > 0:
        try:
            logger.info("Loading existing vector database...")
            db = Chroma(
                persist_directory=persist_directory,
                embedding_function=embeddings
            )
            logger.info(f"Vector database loaded successfully with {db._collection.count()} documents")
            
            return db
        except Exception as e:
            logger.error(f"Error loading existing database: {e}")
            logger.info("Will create a new vector database")
    
    # If no existing database or documents provided, raise an error
    if not documents:
        raise ValueError("No existing database found and no documents provided to create one")
    
    # Create a new vector database
    try:
        logger.info("Creating new vector database...")
        # Split text into chunks - increased chunk size for more context
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        split_documents = text_splitter.split_documents(documents)
        logger.info(f"Split into {len(split_documents)} chunks")
        
        db = Chroma.from_documents(
            split_documents, 
            embeddings, 
            persist_directory=persist_directory
        )
        db.persist()
        logger.info("New vector database created successfully")
        
        return db
    except Exception as e:
        raise RuntimeError(f"Error creating Chroma DB: {e}")

def get_system_prompt(context_type="all"):
    """Get system prompt based on context type"""
    base_prompt = """You are Asha, an AI-powered mentor designed to assist Indian women in career development, 
    job opportunities, entrepreneurship, financial literacy, government schemes, and digital empowerment.
    
    Your responses should be:
    - Detailed and Comprehensive: Provide in-depth information about opportunities, processes, and resources.
    - Simple and Clear: Use easy-to-understand language suitable for users with varying education levels.
    - Structured and Informative: Provide details in a step-by-step manner for clarity.
    - Supportive and Encouraging: Offer practical guidance with a positive and respectful tone.
    - Actionable: Include all necessary details such as eligibility criteria, requirements, application processes, and benefits.
    - Culturally Appropriate: Consider the cultural context of Indian women when providing advice.
    - Gender-inclusive: Avoid gender stereotypes and biases in all responses.
    """
    
    if context_type == "jobs":
        base_prompt += """
        Focus on providing information about job opportunities, application processes, 
        interview preparation, and career guidance for women.
        """
    elif context_type == "events":
        base_prompt += """
        Focus on providing information about upcoming events, workshops, and 
        community programs that would benefit women's career development.
        """
    elif context_type == "mentorship":
        base_prompt += """
        Focus on providing information about mentorship programs, networking 
        opportunities, and professional development resources for women.
        """
    elif context_type == "schemes":
        base_prompt += """
        Focus on providing information about government schemes, subsidies, 
        and programs designed to support women entrepreneurs.
        """
    
    return base_prompt

def query_llm(user_query, context=None, chat_history=None, context_type="all"):
    """Use the LLM with improved context-aware prompt."""
    
    system_message = get_system_prompt(context_type)
    
    messages = [{"role": "system", "content": system_message}]
    
    # Add chat history for better continuity
    if chat_history:
        for message in chat_history[-5:]:  # Include last 5 messages for context
            messages.append(message)
    
    # Format the prompt with context
    if context:
        messages.append({"role": "user", "content": f"Context information (use this to formulate your answer):\n{context}\n\nUser question: {user_query}\n\nProvide a comprehensive, detailed response with all available information on the topic."})
    else:
        messages.append({"role": "user", "content": user_query})
    
    try:
        # Request a longer, more detailed response
        response = llm.invoke(messages)
        return response
    except Exception as e:
        logger.error(f"Error calling LLM API: {e}")
        return f"Error: {str(e)}"

def generate_id():
    """Generate a unique ID for conversations and messages"""
    return str(uuid.uuid4())[:8]

@app.post("/")
async def chat_endpoint(request: ChatRequest):
    try:
        user_query = request.query
        chat_history = request.chat_history
        context_type = request.context_type
        
        logger.info(f"Received query: {user_query}")
        logger.info(f"Context type: {context_type}")
        
        documents = load_documents()
        logger.info(f"Loaded {len(documents)} documents")
        
        db = get_vector_db(documents)
        retriever = db.as_retriever(search_kwargs={"k": 2})
        logger.info("Vector database loaded successfully")

        try:
            context_docs = retriever.get_relevant_documents(user_query)
            context_docs = np.array(context_docs).squeeze().tolist()
            logger.info(f"Retrieved {len(context_docs)} documents.")
        except Exception as e:
            logger.error(f"Error retrieving documents: {e}")
            context_docs = []

        if not context_docs:
            logger.warning("No relevant documents found. Proceeding with general response.")
            context = None
        else:
            context = "\n".join([doc.page_content for doc in context_docs])
        
        chat_history.append({"role": "user", "content": user_query})
        
        response = query_llm(user_query, context, chat_history, context_type)
        
        # Generate unique IDs for tracking
        conversation_id = f"conv_{generate_id()}"
        message_id = f"msg_{generate_id()}"
        
        return {
            "response": response,
            "conversation_id": conversation_id,
            "message_id": message_id,
            "is_biased": False
        }
    
    except Exception as e:
        logger.error(f"Error in API endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/feedback")
async def feedback_endpoint(request: FeedbackRequest):
    """Endpoint to collect user feedback"""
    try:
        # In a real implementation, you would store this in a database
        logger.info(f"Received feedback: {request.feedback_type} for message {request.message_id}")
        
        # For now, just log the feedback
        feedback_data = {
            "conversation_id": request.conversation_id,
            "message_id": request.message_id,
            "feedback_type": request.feedback_type,
            "details": request.details,
            "timestamp": time.time()
        }
        
        logger.info(f"Feedback data: {feedback_data}")
        
        return {"status": "success", "message": "Feedback recorded successfully"}
    
    except Exception as e:
        logger.error(f"Error recording feedback: {e}")
        raise HTTPException(status_code=500, detail=f"Error recording feedback: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)