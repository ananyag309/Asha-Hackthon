import streamlit as st
import requests
import json
import os
from datetime import datetime
import pandas as pd
import time

# Page configuration
st.set_page_config(
    page_title="Asha AI Chatbot",
    page_icon="👩‍💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #6C5B7B;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #8A7090;
        text-align: center;
        margin-bottom: 2rem;
    }
    .user-message {
        background-color: #F1F1F2;
        padding: 1rem;
        border-radius: 15px 15px 15px 0;
        margin: 1rem 2rem 1rem 0;
    }
    .bot-message {
        background-color: #E9D8FD;
        padding: 1rem;
        border-radius: 15px 15px 0 15px;
        margin: 1rem 0 1rem 2rem;
    }
    .category-button {
        background-color: #8A7090;
        color: white;
        border-radius: 20px;
        padding: 0.5rem 1rem;
        margin: 0.5rem;
        border: none;
        cursor: pointer;
        transition: all 0.3s;
    }
    .category-button:hover {
        background-color: #6C5B7B;
        transform: scale(1.05);
    }
    .feature-card {
        background-color: #F9F7FC;
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        border-left: 4px solid #6C5B7B;
    }
    .feedback-button {
        background-color: transparent;
        border: 1px solid #8A7090;
        border-radius: 10px;
        color: #8A7090;
        padding: 0.3rem 0.7rem;
        margin: 0 0.2rem;
        font-size: 0.8rem;
        cursor: pointer;
        transition: all 0.2s;
    }
    .feedback-button:hover {
        background-color: #8A7090;
        color: white;
    }
    .biased-warning {
        background-color: #FFF0F0;
        color: #C53030;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 4px solid #C53030;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state variables
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None
    
if "message_ids" not in st.session_state:
    st.session_state.message_ids = {}

if "current_tab" not in st.session_state:
    st.session_state.current_tab = "chat"
    
if "context_type" not in st.session_state:
    st.session_state.context_type = "all"

# Helper functions - define these first to avoid undefined errors
def send_feedback(conversation_id, message_id, feedback_type, details=None):
    """Send feedback to the backend API or handle locally"""
    try:
        # Store feedback locally
        st.toast(f"Feedback '{feedback_type}' received. Thank you!")
        return True
        
        # Once backend is ready, uncomment this:
        """
        payload = {
            "conversation_id": conversation_id,
            "message_id": message_id,
            "feedback_type": feedback_type,
            "details": details
        }
        
        response = requests.post("http://localhost:8000/feedback", json=payload)
        if response.status_code == 200:
            return True
        return False
        """
    except Exception as e:
        st.error(f"Error sending feedback: {e}")
        return False

def process_query(query):
    """Process the user query and get response from backend"""
    if not query.strip():
        st.warning("Please enter a question.")
        return
    
    # Add user message to chat history
    st.session_state.chat_history.append({"role": "user", "content": query})
    
    # Clear the input field
    st.session_state.query = ""
    
    # Prepare payload for the API
    payload = {
        "query": query,
        "chat_history": st.session_state.chat_history,
        "context_type": st.session_state.context_type
    }
    
    try:
        # Show a spinner while waiting for response
        with st.spinner("Asha is thinking..."):
            # Make API call to backend
            response = requests.post("http://localhost:8000/", json=payload)
            response_data = response.json()
            
            # Check for biased content warning
            if response_data.get("is_biased", False):
                st.warning(response_data["response"])
            else:
                # Update conversation state
                st.session_state.conversation_id = response_data.get("conversation_id")
                message_id = response_data.get("message_id")
                
                # Add bot response to chat history with message_id for feedback
                bot_message = {
                    "role": "assistant", 
                    "content": response_data["response"],
                    "message_id": message_id
                }
                st.session_state.chat_history.append(bot_message)
                
                # Store message_id for feedback
                if message_id:
                    st.session_state.message_ids[message_id] = len(st.session_state.chat_history) - 1
        
        # Force the UI to refresh and show the new messages
        st.rerun()
            
    except Exception as e:
        st.error(f"Error communicating with Asha: {e}")
        # Add error message to chat history
        st.session_state.chat_history.append({
            "role": "assistant", 
            "content": "I'm sorry, I encountered an error while processing your request. Please try again later."
        })
        st.rerun()

def set_job_query(job):
    """Set query about a specific job"""
    st.session_state.query = f"Tell me more about the {job['title']} position at {job['company']} and help me prepare to apply"
    st.session_state.current_tab = "chat"
    st.rerun()

def set_event_query(event):
    """Set query about a specific event"""
    st.session_state.query = f"Tell me more about the '{event['title']}' event on {event['date']} and what I can gain from it"
    st.session_state.current_tab = "chat"
    st.rerun()

def set_mentorship_query(program):
    """Set query about a specific mentorship program"""
    st.session_state.query = f"Tell me how to prepare for applying to the '{program['title']}' mentorship program by {program['organization']}"
    st.session_state.current_tab = "chat"
    st.rerun()

def fetch_jobs_for_ui():
    """Fetch job listings for UI display"""
    try:
        job_listings_file = "job_listings.json"
        
        if not os.path.exists(job_listings_file):
            # Create sample data
            sample_jobs = [
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
            
            with open(job_listings_file, "w", encoding="utf-8") as f:
                json.dump(sample_jobs, f, indent=2)
            
            return sample_jobs
        
        # Read job listings
        with open(job_listings_file, "r", encoding="utf-8") as f:
            all_jobs = json.load(f)
        
        return all_jobs
        
    except Exception as e:
        st.error(f"Error fetching job listings: {e}")
        return []

def fetch_events_for_ui():
    """Fetch events for UI display"""
    try:
        events_file = "community_events.json"
        
        if not os.path.exists(events_file):
            # Create sample data
            sample_events = [
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
                json.dump(sample_events, f, indent=2)
            
            return sample_events
        
        # Read events
        with open(events_file, "r", encoding="utf-8") as f:
            all_events = json.load(f)
        
        return all_events
        
    except Exception as e:
        st.error(f"Error fetching events: {e}")
        return []

def fetch_mentorship_for_ui():
    """Fetch mentorship programs for UI display"""
    try:
        mentorship_file = "mentorship_programs.json"
        
        if not os.path.exists(mentorship_file):
            # Create sample data
            sample_mentorships = [
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
                json.dump(sample_mentorships, f, indent=2)
            
            return sample_mentorships
        
        # Read mentorship programs
        with open(mentorship_file, "r", encoding="utf-8") as f:
            all_mentorships = json.load(f)
        
        return all_mentorships
        
    except Exception as e:
        st.error(f"Error fetching mentorship programs: {e}")
        return []
    
    

# Header
st.markdown("<h1 class='main-header'>👩‍💼 Asha AI Chatbot</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>Your guide to career growth, job opportunities, and professional development</p>", unsafe_allow_html=True)

# Tabs for different sections
tabs = st.tabs(["💬 Chat", "🔍 Jobs", "📅 Events", "👩‍🏫 Mentorship", "📊 Analytics"])

# Chat Tab
with tabs[0]:
    if st.session_state.current_tab != "chat":
        st.session_state.current_tab = "chat"
    
    # Sidebar for chat settings and filters
    with st.sidebar:
        st.header("Chat Settings")
        
        st.subheader("Filter Responses By")
        context_options = {
            "all": "All Information",
            "jobs": "Job Listings",
            "events": "Community Events",
            "mentorship": "Mentorship Programs",
            "schemes": "Government Schemes"
        }
        
        selected_context = st.radio(
            "Focus on specific information:",
            list(context_options.keys()),
            format_func=lambda x: context_options[x],
            index=list(context_options.keys()).index(st.session_state.context_type)
        )
        
        if selected_context != st.session_state.context_type:
            st.session_state.context_type = selected_context
        
        st.markdown("---")
        
        # Suggested questions based on categories
        st.subheader("Suggested Questions")
        
        # Career Development Questions
        st.markdown("##### 🚀 Career Development")
        career_questions = [
            "What career paths have good growth opportunities for women?",
            "How can I build a career in technology with no prior experience?",
            "What skills should I develop to advance in my career?",
            "How can I balance my career with family responsibilities?",
            "What certifications will help me in a digital marketing career?"
        ]
        
        for question in career_questions:
            if st.button(question, key=f"career_{question}"):
                st.session_state.query = question
                st.rerun()
        
        # Job Search Questions
        st.markdown("##### 💼 Job Opportunities")
        job_questions = [
            "What job opportunities are available for women returning to work?",
            "Are there any remote job opportunities available?",
            "How can I prepare for a job interview?",
            "What women-friendly companies are hiring now?",
            "What should I include in my resume to stand out?"
        ]
        
        for question in job_questions:
            if st.button(question, key=f"job_{question}"):
                st.session_state.query = question
                st.rerun()
        
        # Events & Programs Questions
        st.markdown("##### 📣 Events & Mentorship")
        event_questions = [
            "Are there any upcoming workshops for women in tech?",
            "How can I find a mentor in my field?",
            "Tell me about upcoming career development sessions",
            "What networking events are happening soon?",
            "How can I register for mentorship programs?"
        ]
        
        for question in event_questions:
            if st.button(question, key=f"event_{question}"):
                st.session_state.query = question
                st.rerun()
    
     # Input field for user query
   
    user_query = st.text_input(
        "💬 Ask Asha about careers, jobs, events, or mentorship...",
        value=getattr(st.session_state, 'query', ""),
        key="query_input"
    )
    
    # Chat interface
    st.subheader("Your Conversation")
    
    # Display conversation history
    chat_container = st.container(height=400)
    with chat_container:
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.markdown(f"<div class='user-message'><b>You:</b> {message['content']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='bot-message'><b>Asha:</b> {message['content']}</div>", unsafe_allow_html=True)
                
                # Add feedback buttons for bot messages
                if message.get("message_id"):
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("👍 Helpful", key=f"helpful_{message['message_id']}"):
                            send_feedback(st.session_state.conversation_id, message["message_id"], "helpful")
                            st.toast("Thank you for your feedback!")
                    with col2:
                        if st.button("👎 Not Helpful", key=f"not_helpful_{message['message_id']}"):
                            send_feedback(st.session_state.conversation_id, message["message_id"], "not_helpful")
                            st.toast("Thank you for your feedback! We'll use it to improve.")
                    

   
    
   
    col1, col2 = st.columns([1, 1])
    
    with col1:
        if st.button("🔍 Send", use_container_width=True):
            process_query(user_query)
            
    with col2:
        if st.button("🧹 Clear Chat", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.conversation_id = None
            st.session_state.message_ids = {}
            st.rerun()
    
    

# Jobs Tab
with tabs[1]:
    if st.session_state.current_tab != "jobs":
        st.session_state.current_tab = "jobs"
        
    st.header("Job Opportunities")
    
    # Job search filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        job_search = st.text_input("Search jobs by title, skills, or location:", key="job_search")
    
    with col2:
        job_location = st.selectbox(
            "Location:",
            ["All Locations", "Remote", "Bangalore", "Delhi", "Mumbai", "Hyderabad", "Chennai", "Other"]
        )
    
    with col3:
        job_type = st.selectbox(
            "Job Type:",
            ["All Types", "Full-time", "Part-time", "Remote", "Flexible", "Internship"]
        )
    
    # Fetch and display jobs
    try:
        if job_search or job_location != "All Locations" or job_type != "All Types":
            # This would be an API call in a real implementation
            # For now, we'll use sample data
            st.info("Filtering jobs based on your criteria...")
            time.sleep(1)  # Simulate API call
        
        # Display job listings in card format
        job_data = fetch_jobs_for_ui()
        
        if not job_data:
            st.warning("No job listings found. Please try different search criteria.")
        else:
            for job in job_data:
                with st.container():
                    st.markdown(f"""
                    <div class='feature-card'>
                        <h3>{job['title']}</h3>
                        <p><b>Company:</b> {job['company']}</p>
                        <p><b>Location:</b> {job['location']}</p>
                        <p><b>Salary:</b> {job['salary']}</p>
                        <p>{job['description']}</p>
                        <p><b>Women-friendly benefits:</b> {', '.join(job['women_friendly_benefits'])}</p>
                        <p><i>Posted on: {job['posted_date']}</i></p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns([1, 5])
                    with col1:
                        st.button("Apply Now", key=f"apply_{job['id']}")
                    with col2:
                        if st.button("Ask Asha about this job", key=f"ask_{job['id']}"):
                            set_job_query(job)
    except Exception as e:
        st.error(f"Error loading job listings: {e}")

# Events Tab
with tabs[2]:
    if st.session_state.current_tab != "events":
        st.session_state.current_tab = "events"
        
    st.header("Community Events & Workshops")
    
    # Event filters
    col1, col2 = st.columns(2)
    
    with col1:
        event_search = st.text_input("Search events by title or topic:", key="event_search")
    
    with col2:
        event_type = st.selectbox(
            "Event Type:",
            ["All Events", "Workshops", "Conferences", "Networking", "Career Development", "Skill Building"]
        )
    
    # Timeline view toggle
    show_timeline = st.toggle("Show Timeline View", value=False)
    
    # Fetch and display events
    try:
        # This would be an API call in a real implementation
        event_data = fetch_events_for_ui()
        
        if not event_data:
            st.warning("No upcoming events found.")
        else:
            if show_timeline:
                # Timeline view
                timeline_data = []
                for event in event_data:
                    timeline_data.append({
                        "Date": pd.to_datetime(event['date']),
                        "Event": event['title'],
                        "Organizer": event['organizer'],
                        "Type": "Online" if event.get('online', False) else "In-person"
                    })
                
                timeline_df = pd.DataFrame(timeline_data)
                timeline_df = timeline_df.sort_values("Date")
                
                st.line_chart(timeline_df.set_index("Date").reset_index(drop=True))
                st.dataframe(timeline_df)
            else:
                # Card view
                for event in event_data:
                    with st.container():
                        online_badge = "🌐 Online" if event.get('online', False) else "🏢 In-person"
                        free_badge = "🆓 Free" if event.get('is_free', False) else f"💰 {event.get('fee', 'Paid')}"
                        
                        st.markdown(f"""
                        <div class='feature-card'>
                            <h3>{event['title']} <span style="font-size:0.8rem;background-color:#E2E8F0;padding:0.2rem 0.5rem;border-radius:10px;margin-left:0.5rem;">{online_badge}</span> <span style="font-size:0.8rem;background-color:#E2E8F0;padding:0.2rem 0.5rem;border-radius:10px;margin-left:0.5rem;">{free_badge}</span></h3>
                            <p><b>Organizer:</b> {event['organizer']}</p>
                            <p><b>Date:</b> {event['date']} | <b>Time:</b> {event.get('time', 'TBD')}</p>
                            <p><b>Location:</b> {event['location']}</p>
                            <p>{event.get('description', '')}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col1, col2 = st.columns([1, 5])
                        with col1:
                            st.button("Register", key=f"register_{event['id']}")
                        with col2:
                            if st.button("Ask Asha about this event", key=f"ask_event_{event['id']}"):
                                set_event_query(event)
    except Exception as e:
        st.error(f"Error loading events: {e}")

# Mentorship Tab
with tabs[3]:
    if st.session_state.current_tab != "mentorship":
        st.session_state.current_tab = "mentorship"
        
    st.header("Mentorship Programs")
    
    # Mentorship filters
    col1, col2 = st.columns(2)
    
    with col1:
        mentorship_search = st.text_input("Search by expertise or industry:", key="mentorship_search")
    
    with col2:
        duration_filter = st.selectbox(
            "Duration:",
            ["Any Duration", "1-3 months", "3-6 months", "6+ months"]
        )
    
    # Fetch and display mentorship programs
    try:
        mentorship_data = fetch_mentorship_for_ui()
        
        if not mentorship_data:
            st.warning("No mentorship programs found.")
        else:
            for program in mentorship_data:
                with st.container():
                    st.markdown(f"""
                    <div class='feature-card'>
                        <h3>{program['title']}</h3>
                        <p><b>Organization:</b> {program['organization']}</p>
                        <p><b>Duration:</b> {program['duration']} | <b>Format:</b> {program['format']}</p>
                        <p>{program['description']}</p>
                        <p><b>Mentor Expertise:</b> {', '.join(program['mentor_expertise'])}</p>
                        <p><b>Application Deadline:</b> {program['application_deadline']}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col1, col2 = st.columns([1, 5])
                    with col1:
                        st.button("Apply", key=f"apply_mentor_{program['id']}")
                    with col2:
                        if st.button("Ask Asha about this program", key=f"ask_mentor_{program['id']}"):
                            set_mentorship_query(program)
    except Exception as e:
        st.error(f"Error loading mentorship programs: {e}")

# Analytics Tab
with tabs[4]:
    if st.session_state.current_tab != "analytics":
        st.session_state.current_tab = "analytics"
        
    st.header("Chatbot Analytics & Insights")
    
    # Sample analytics data
    st.subheader("User Engagement")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Active Users", "127", "+12%")
    with col2:
        st.metric("Avg. Session Duration", "8.2 min", "+5%")
    with col3:
        st.metric("Queries per User", "5.3", "-2%")
    
    # Sample chart
    st.subheader("Query Categories")
    chart_data = pd.DataFrame({
        'Category': ['Job Search', 'Career Advice', 'Events', 'Mentorship', 'Skills', 'Other'],
        'Percentage': [32, 24, 18, 14, 8, 4]
    })
    st.bar_chart(chart_data.set_index('Category'))
    
    # Sample feedback metrics
    st.subheader("User Feedback")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Helpful Responses", "89%", "+3%")
    with col2:
        st.metric("Response Accuracy", "92%", "+5%")
    with col3:
        st.metric("Bias Detection", "99.7%", "+1%")
    
    # Recent improvements
    st.subheader("Recent Improvements")
    improvements = [
        "Added more comprehensive job listings from multiple sources",
        "Improved mentorship program matching algorithm",
        "Enhanced bias detection for more inclusive responses",
        "Added real-time event updates from community partners",
        "Optimized response time for career guidance queries"
    ]
    
    for improvement in improvements:
        st.markdown(f"✅ {improvement}")

# Footer
st.markdown("---")
footer_col1, footer_col2, footer_col3 = st.columns([2, 1, 2])
with footer_col2:
    st.markdown("<p style='text-align: center;'>Powered by JobsForHer Foundation</p>", unsafe_allow_html=True)

# Create needed files at startup
if not os.path.exists("job_listings.json"):
    fetch_jobs_for_ui()

if not os.path.exists("community_events.json"):
    fetch_events_for_ui()

if not os.path.exists("mentorship_programs.json"):
    fetch_mentorship_for_ui()