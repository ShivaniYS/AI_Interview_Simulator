import streamlit as st
import json
from datetime import datetime
import tempfile
import os
from fpdf import FPDF
import base64
import io
import random
from dotenv import load_dotenv

# Try to import OpenAI, will show error if not installed
try:
    from openai import OpenAI
    openai_available = True
except ImportError:
    openai_available = False
    st.error("OpenAI package not installed. Run: pip install openai")

# Load environment variables from .env file (for local development)
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Ai Interview Practice",
    page_icon="💻",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== API KEY SETUP ==========
# Try multiple ways to get API key (Streamlit Cloud compatible)
api_key = None
api_configured = False

# Method 1: Try Streamlit secrets (for Streamlit Cloud)
try:
    if 'OPENAI_API_KEY' in st.secrets:
        api_key = st.secrets['OPENAI_API_KEY']
       
except:
    pass

# Method 2: Try environment variable (for local development)
if not api_key:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        st.info("ℹ️ API key loaded from .env file")

# Method 3: Try direct input (fallback)
if not api_key:
    with st.sidebar.expander("🔐 API Configuration", expanded=False):
        api_key = st.text_input(
            "Enter your OpenAI API key:",
            type="password",
            help="Get your API key from https://platform.openai.com/api-keys"
        )
        if api_key:
            st.success("API key entered. It will be used for this session only.")
        else:
            st.warning("⚠️ No API key found. Running in demo mode with simulated responses.")

# Initialize OpenAI client if API key is available
openai_client = None
if api_key and api_key.startswith("sk-") and openai_available:
    try:
        openai_client = OpenAI(api_key=api_key)
        # Test the connection
        openai_client.models.list()
        api_configured = True
        st.session_state.openai_client = openai_client
        st.session_state.api_configured = True
       
            
    except Exception as e:
        st.error(f"OpenAI API configuration failed: {str(e)[:100]}")
        api_configured = False
        openai_client = None
elif api_key and not api_key.startswith("sk-"):
    st.warning("⚠️ Invalid OpenAI API key format. Should start with 'sk-'. Running in demo mode.")
    api_configured = False
else:
    if not openai_available:
        st.error("OpenAI package not installed. Install with: pip install openai")
    api_configured = False

# Initialize session state
if 'progress' not in st.session_state:
    st.session_state.progress = {
        'completed': [],
        'scores': {},
        'answers': {},
        'transcripts': {},
        'evaluations': {}
    }

if 'api_configured' not in st.session_state:
    st.session_state.api_configured = api_configured
if 'openai_client' not in st.session_state:
    st.session_state.openai_client = openai_client

# ========== QUESTIONS DATABASE ==========
QUESTIONS = [
    {
        "id": 1,
        "category": "Data Structures",
        "question": "Explain the difference between an array and a linked list.",
        "keywords": ["array", "linked list", "memory allocation", "access time", "insertion", "deletion"],
        "ideal_length": "250-500 words",
        "difficulty": "Medium",
        "demo_transcripts": [
            "Arrays and linked lists are both linear data structures but differ significantly in memory allocation. Arrays use contiguous memory blocks, allowing O(1) access time but making insertions/deletions expensive at O(n). Linked lists use non-contiguous memory with pointers, providing O(1) insertions/deletions but O(n) access time. Arrays have fixed size while linked lists are dynamic.",
            "The key difference lies in memory organization. Arrays allocate contiguous memory, making cache utilization efficient but resizing costly. Linked lists use scattered memory with nodes containing data and next pointers, enabling efficient insertions but poor cache locality. Arrays support random access; linked lists require sequential traversal."
        ]
    },
    {
        "id": 2,
        "category": "Algorithms",
        "question": "What is the time complexity of binary search and how does it work?",
        "keywords": ["binary search", "time complexity", "O(log n)", "sorted array", "divide and conquer"],
        "ideal_length": "100-200 words",
        "difficulty": "Easy",
        "demo_transcripts": [
            "Binary search has O(log n) time complexity. It works by repeatedly dividing a sorted array in half. You start with the middle element - if it matches the target, you're done. If the target is smaller, search the left half; if larger, search the right half. Continue until found or the search space is empty. It requires the array to be sorted.",
            "Binary search operates in O(log n) time. The algorithm compares the target value to the middle element of a sorted array. Based on comparison, it eliminates half of the remaining elements. This divide-and-conquer approach dramatically reduces search time compared to linear search's O(n)."
        ]
    },
    {
        "id": 3,
        "category": "System Design",
        "question": "How would you design a URL shortening service like bit.ly?",
        "keywords": ["hash function", "database", "scalability", "cache", "redirect", "unique ID"],
        "ideal_length": "300-500 words",
        "difficulty": "Hard",
        "demo_transcripts": [
            "A URL shortener needs several components: a unique ID generator using hash functions like Base62, a database to map short codes to original URLs, a caching layer like Redis for frequent URLs, and a redirect service. The system must handle high traffic, ensure collision-free hashing, and provide analytics. Considerations include scalability, cache invalidation, and monitoring.",
            "Key components include: 1) Encoding service that converts long URLs to short codes using hash algorithms, 2) Database storage for mappings, 3) Cache for popular URLs, 4) Redirect service with 301/302 responses, 5) Analytics tracking. Design considerations: load balancing, database sharding, CDN usage, and rate limiting."
        ]
    },
    {
        "id": 4,
        "category": "Algorithms",
        "question": "Explain how a hash table works and its time complexity.",
        "keywords": ["hash function", "collision", "bucket", "load factor", "O(1)", "chaining"],
        "ideal_length": "150-300 words",
        "difficulty": "Medium",
        "demo_transcripts": [
            "Hash tables map keys to values using a hash function that converts keys to array indices. They offer average O(1) time for insert, delete, and search operations. Collisions occur when different keys hash to the same index, resolved via chaining (linked lists) or open addressing. Load factor triggers resizing to maintain efficiency.",
            "A hash table uses a hash function to compute an index into an array of buckets. Ideally, this provides O(1) average-case complexity. Collision resolution methods include separate chaining and open addressing. Performance degrades with high load factor, requiring rehashing. Good hash functions distribute keys uniformly."
        ]
    },
    {
        "id": 5,
        "category": "Data Structures",
        "question": "What are the differences between a stack and a queue?",
        "keywords": ["LIFO", "FIFO", "operations", "use cases", "implementation"],
        "ideal_length": "100-200 words",
        "difficulty": "Easy",
        "demo_transcripts": [
            "Stacks follow LIFO (Last-In-First-Out) with push/pop operations, used for function calls, undo operations, and parsing. Queues follow FIFO (First-In-First-Out) with enqueue/dequeue operations, used for task scheduling, BFS, and messaging systems. Both can be implemented using arrays or linked lists with different access patterns.",
            "Key difference: access order. Stack is LIFO - last element added is first removed. Queue is FIFO - first element added is first removed. Common stack operations: push, pop, peek. Queue operations: enqueue, dequeue, front. Stacks for recursion/backtracking, queues for breadth-first processing."
        ]
    },
    {
        "id": 6,
        "category": "System Design",
        "question": "Describe how you would design a simple chat application.",
        "keywords": ["real-time", "websockets", "database", "scalability", "message queue", "authentication"],
        "ideal_length": "250-400 words",
        "difficulty": "Hard",
        "demo_transcripts": [
            "A chat app requires: 1) WebSocket connections for real-time communication, 2) Message broker for distribution, 3) Database for message persistence, 4) Authentication service, 5) Notification service for offline users. Design considerations: connection management, message ordering, read receipts, typing indicators, and media handling.",
            "Core components include: client-server WebSocket connections, message queue (Kafka/RabbitMQ) for decoupling, database (SQL for users, NoSQL for messages), caching for active sessions, and push notification service. Must handle concurrent connections, message delivery guarantees, and presence tracking."
        ]
    },
    {
        "id": 7,
        "category": "Behavioral",
        "question": "Tell me about a challenging project you worked on and how you overcame obstacles.",
        "keywords": ["challenge", "solution", "teamwork", "learning", "results"],
        "ideal_length": "200-350 words",
        "difficulty": "Medium",
        "demo_transcripts": [
            "I worked on a legacy system migration with tight deadlines. Challenges included undocumented APIs and team knowledge gaps. I overcame this by creating detailed documentation, pairing with senior engineers, and implementing incremental migration with feature flags. The project completed on time with zero downtime.",
            "The most challenging project involved optimizing database queries that were causing performance issues. I systematically analyzed query patterns, implementing indexing strategies, introduced caching, and refactored inefficient joins. Through careful monitoring and A/B testing, we achieved 70% performance improvement."
        ]
    },
    {
        "id": 8,
        "category": "Algorithms",
        "question": "What is dynamic programming and when would you use it?",
        "keywords": ["memoization", "optimal substructure", "overlapping subproblems", "Fibonacci", "examples"],
        "ideal_length": "150-250 words",
        "difficulty": "Medium",
        "demo_transcripts": [
            "Dynamic programming solves complex problems by breaking them into overlapping subproblems and storing solutions to avoid recomputation. It applies when problems have optimal substructure and overlapping subproblems. Examples: Fibonacci sequence, knapsack problem, shortest path algorithms. Techniques include memoization (top-down) and tabulation (bottom-up).",
            "DP optimizes recursive solutions by caching intermediate results. Use it for problems where the same subproblems recur, like calculating Fibonacci numbers or finding the longest common subsequence. The key insight is trading space for time by storing computed results in a table or dictionary."
        ]
    },
    {
        "id": 9,
        "category": "Data Structures",
        "question": "Compare and contrast B-trees and binary search trees.",
        "keywords": ["balanced", "height", "disk access", "database indexing", "nodes", "children"],
        "ideal_length": "150-250 words",
        "difficulty": "Hard",
        "demo_transcripts": [
            "B-trees are balanced m-way trees optimized for disk access, with nodes containing multiple keys and children. Binary search trees are binary trees with at most two children per node. B-trees minimize disk I/O by having larger node sizes matching disk blocks, while BSTs are memory-optimized. B-trees auto-balance, BSTs may become unbalanced.",
            "Key differences: B-trees have multiple keys per node and maintain balance automatically, making them ideal for databases and file systems. BSTs have one key per node and can degrade to O(n) if unbalanced. B-trees have lower height, reducing disk accesses for large datasets stored externally."
        ]
    },
    {
        "id": 10,
        "category": "Behavioral",
        "question": "How do you handle conflicts when working in a team?",
        "keywords": ["communication", "compromise", "perspective", "resolution", "professionalism"],
        "ideal_length": "150-250 words",
        "difficulty": "Medium",
        "demo_transcripts": [
            "I handle conflicts through open communication, focusing on issues not people. First, I listen to understand all perspectives. Then, I facilitate discussion to find common ground, proposing data-driven solutions. If needed, I escalate to a manager. The goal is constructive resolution that strengthens the team, not winning arguments.",
            "My approach: 1) Address issues early before escalation, 2) Focus on facts and project goals, 3) Seek compromise through brainstorming alternatives, 4) Document agreements, 5) Follow up to ensure resolution. I believe diverse perspectives strengthen outcomes when managed constructively."
        ]
    }
]

# ========== HELPER FUNCTIONS ==========
def clear_question_data(qid):
    """Clear UI state for a specific question"""
    keys_to_clear = []
    
    for key in list(st.session_state.keys()):
        if key.startswith(f'audio_transcript_{qid}') or \
           key.startswith(f'text_answer_{qid}') or \
           key.startswith(f'last_audio_{qid}') or \
           key.startswith(f'audio_input_{qid}') or \
           key.startswith(f'audio_uploaded_{qid}') or \
           key.startswith(f'audio_recorder_{qid}') or \
           key.startswith(f'transcript_display_{qid}') or \
           key.startswith(f'record_count_{qid}') or \
           key.startswith(f'recording_active_{qid}') or \
           key.startswith(f'audio_data_{qid}'):
            keys_to_clear.append(key)
    
    keys_to_clear = list(set(keys_to_clear))
    for key in keys_to_clear:
        try:
            del st.session_state[key]
        except:
            pass
    
    # Clear from progress tracking
    progress = st.session_state.progress
    qid_str = str(qid)
    
    if qid_str in progress['answers']:
        del progress['answers'][qid_str]
    if qid_str in progress['scores']:
        del progress['scores'][qid_str]
    if qid_str in progress['completed']:
        progress['completed'] = [q for q in progress['completed'] if q != qid_str]
    if qid_str in progress['transcripts']:
        del progress['transcripts'][qid_str]
    if qid_str in progress['evaluations']:
        del progress['evaluations'][qid_str]
    
    return True

def reset_all_progress():
    """Reset ALL progress including stored answers"""
    st.session_state.progress = {
        'completed': [],
        'scores': {},
        'answers': {},
        'transcripts': {},
        'evaluations': {}
    }
    
    keys_to_clear = [k for k in st.session_state.keys() if k not in [
        'api_configured', 'openai_client', 'page', 'progress'
    ]]
    
    for key in keys_to_clear:
        try:
            del st.session_state[key]
        except:
            pass
    
    return True

def get_audio_size(audio_data):
    """Get size of audio data in KB, handling both UploadedFile and bytes"""
    if audio_data is None:
        return 0
    
    if hasattr(audio_data, 'getvalue'):
        return len(audio_data.getvalue()) // 1024
    elif isinstance(audio_data, bytes):
        return len(audio_data) // 1024
    else:
        return 0

def get_audio_bytes(audio_data):
    """Extract bytes from audio data, handling both UploadedFile and bytes"""
    if audio_data is None:
        return None
    
    if hasattr(audio_data, 'getvalue'):
        return audio_data.getvalue()
    elif isinstance(audio_data, bytes):
        return audio_data
    else:
        return None

def audio_recorder_component(question_id):
    """Custom audio recorder component"""
    qid = str(question_id)
    
    if f'recording_active_{qid}' not in st.session_state:
        st.session_state[f'recording_active_{qid}'] = False
    if f'record_count_{qid}' not in st.session_state:
        st.session_state[f'record_count_{qid}'] = 0
    
    st.write("### 🎤 Record Your Answer")
    
    last_audio_key = f'last_audio_{qid}'
    
    if last_audio_key in st.session_state and st.session_state[last_audio_key] is not None:
        st.success("✅ Audio recorded!")
        
        audio_bytes = get_audio_bytes(st.session_state[last_audio_key])
        if audio_bytes:
            st.audio(audio_bytes, format="audio/wav")
        
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("🔄 Re-record", 
                       key=f"rerecord_main_{qid}",
                       use_container_width=True,
                       help="Record a new audio, replacing current one"):
                st.session_state[last_audio_key] = None
                st.session_state[f'recording_active_{qid}'] = True
                st.session_state[f'record_count_{qid}'] += 1
                for key in list(st.session_state.keys()):
                    if key.startswith(f'audio_recorder_{qid}'):
                        try:
                            del st.session_state[key]
                        except:
                            pass
                st.rerun()
    
    elif st.session_state[f'recording_active_{qid}']:
        record_key = f"audio_recorder_{qid}_{st.session_state[f'record_count_{qid}']}"
        
        audio_bytes = st.audio_input(
            "Click to start/stop recording",
            key=record_key
        )
        
        if audio_bytes is not None:
            st.session_state[last_audio_key] = audio_bytes
            st.session_state[f'recording_active_{qid}'] = False
            st.success("✅ Recording complete!")
            st.rerun()
        
        if st.button("❌ Cancel Recording", 
                   key=f"cancel_record_{qid}",
                   use_container_width=True,
                   type="secondary"):
            st.session_state[f'recording_active_{qid}'] = False
            st.rerun()
    
    else:
        if st.button("🎤 Start Recording", 
                    key=f"start_record_{qid}",
                    use_container_width=True,
                    type="primary"):
            st.session_state[f'recording_active_{qid}'] = True
            st.session_state[f'record_count_{qid}'] += 1
            st.rerun()

def show_sidebar():
    with st.sidebar:
        st.title("⚙️ Configuration")
        
        if st.session_state.api_configured:
            st.success("✅ OpenAI API Configured")
            if 'OPENAI_API_KEY' in st.secrets:
                st.caption("API key loaded from Streamlit secrets")
            else:
                st.caption("API key loaded from .env file or manual input")
        else:
            st.warning("⚠️ Running in Demo Mode")
            st.caption("Add OpenAI API key to enable full features")
        
        st.divider()
        
        st.subheader("📊 Quick Stats")
        progress = st.session_state.progress
        completed = len(progress['completed'])
        attempted = len(progress.get('answers', {}))
        
        st.metric("Questions Completed", f"{completed}/{len(QUESTIONS)}")
        st.caption(f"Attempted: {attempted}")
        
        if progress['scores']:
            avg_score = sum(progress['scores'].values()) / len(progress['scores'])
            st.metric("Average Score", f"{avg_score:.1f}%")
        
        st.divider()
        
        st.subheader("🚀 Navigation")
        page_options = {
            "🏠 Home": "home",
            "📝 Practice": "practice",
            "📊 Dashboard": "dashboard",
            "📄 Report": "report"
        }
        
        page_labels = list(page_options.keys())
        current_page = st.session_state.get('page', 'home')
        
        current_index = 0
        for i, (label, page) in enumerate(page_options.items()):
            if page == current_page:
                current_index = i
                break
        
        selected_label = st.radio(
            "Go to:",
            page_labels,
            index=current_index,
            label_visibility="collapsed"
        )
        
        st.session_state.page = page_options[selected_label]
        
        st.divider()
        
        if st.button("🔄 Reset All Progress", use_container_width=True, type="secondary"):
            if reset_all_progress():
                st.success("All progress cleared!")
                st.rerun()
        
        st.divider()
        st.caption("💡 Tip: Record audio, then transcribe and evaluate for best results")

def get_question_demo_transcript(question_id):
    """Get appropriate demo transcript for specific question"""
    for q in QUESTIONS:
        if q['id'] == question_id:
            if 'demo_transcripts' in q and q['demo_transcripts']:
                return random.choice(q['demo_transcripts'])
            else:
                category = q['category']
                if category == "Data Structures":
                    return "Data structures organize and store data efficiently. Different structures optimize for different operations like access, insertion, or deletion."
                elif category == "Algorithms":
                    return "Algorithms are step-by-step procedures for solving problems. Time and space complexity analysis helps compare algorithm efficiency."
                elif category == "System Design":
                    return "System design involves creating scalable, reliable architectures. Key considerations include load balancing, caching, database choice, and fault tolerance."
                elif category == "Behavioral":
                    return "Behavioral questions assess soft skills and experience. Use the STAR method (Situation, Task, Action, Result) to structure responses."
    return "This is a demo transcript for a technical interview question."

def transcribe_audio(audio_data, question_id=None):
    """Transcribe audio using Whisper"""
    if not st.session_state.api_configured:
        if question_id:
            return get_question_demo_transcript(question_id)
        return "API not configured. Please add OpenAI API key to enable transcription."
    
    try:
        audio_bytes = get_audio_bytes(audio_data)
        if audio_bytes is None:
            raise ValueError("No audio data found")
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_bytes)
            tmp_path = tmp_file.name
        
        with open(tmp_path, "rb") as audio:
            transcript = st.session_state.openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio
            )
        
        os.unlink(tmp_path)
        return transcript.text
    except Exception as e:
        st.error(f"Transcription error: {str(e)[:100]}")
        if question_id:
            return get_question_demo_transcript(question_id)
        return "Error in transcription. Please try again."

def evaluate_with_gpt(question, answer):
    """Evaluate answer using GPT - Simplified and more accurate"""
    if not st.session_state.api_configured:
        return get_demo_feedback(question)
    
    try:
        prompt = f"""
        You are a technical interview evaluator. Evaluate this answer for an interview question.
        
        QUESTION: {question['question']}
        CATEGORY: {question['category']}
        DIFFICULTY: {question['difficulty']}
        KEY CONCEPTS: {', '.join(question['keywords'])}
        
        STUDENT'S ANSWER: {answer}
        
        Provide a SINGLE overall score from 0-100 based on:
        1. Technical accuracy and correctness
        2. Completeness - covering all key concepts
        3. Clarity and organization
        4. Depth of understanding
        5. Conciseness - appropriate length
        
        Scoring guidelines:
        - 90-100: Excellent - Comprehensive, accurate, well-structured
        - 80-89: Very Good - Solid understanding, minor improvements needed
        - 70-79: Good - Understands concepts, needs more depth
        - 60-69: Satisfactory - Basic understanding, some gaps
        - 50-59: Needs Work - Significant gaps or inaccuracies
        - Below 50: Poor - Major issues or incomplete
        
        Provide evaluation in this exact format:
        SCORE: [single number 0-100]
        STRENGTHS: [2-3 specific strengths]
        IMPROVEMENTS: [2-3 specific areas for improvement]
        FEEDBACK: [3-4 sentences with specific feedback]
        
        Be honest and realistic in scoring. A poor answer should get a low score.
        """
        
        response = st.session_state.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a realistic technical interviewer. Score honestly based on answer quality."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        response_text = response.choices[0].message.content
        
        result = {
            "score": 50,  # Default score
            "strengths": [],
            "improvements": [],
            "feedback": ""
        }
        
        lines = response_text.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('SCORE:'):
                try:
                    score_text = line.replace('SCORE:', '').strip()
                    result["score"] = int(score_text)
                except:
                    result["score"] = 50
            elif line.startswith('STRENGTHS:'):
                strengths_text = line.replace('STRENGTHS:', '').strip()
                result["strengths"] = [s.strip() for s in strengths_text.split(',') if s.strip()]
            elif line.startswith('IMPROVEMENTS:'):
                improvements_text = line.replace('IMPROVEMENTS:', '').strip()
                result["improvements"] = [i.strip() for i in improvements_text.split(',') if i.strip()]
            elif line.startswith('FEEDBACK:'):
                feedback_text = line.replace('FEEDBACK:', '').strip()
                result["feedback"] = feedback_text
        
        if not result["strengths"]:
            result["strengths"] = ["Clear communication", "Good attempt"]
        if not result["improvements"]:
            result["improvements"] = ["Add more technical details", "Be more specific"]
        if not result["feedback"]:
            result["feedback"] = "Good effort. Consider providing more specific technical details and examples to improve your answer."
        
        return result
    
    except Exception as e:
        st.error(f"GPT Evaluation error: {str(e)[:100]}")
        return get_demo_feedback(question)

def get_demo_feedback(question):
    """Return demo feedback when in demo mode"""
    category = question['category']
    difficulty = question['difficulty']
    
    if difficulty == "Easy":
        base_score = random.randint(70, 90)
    elif difficulty == "Medium":
        base_score = random.randint(60, 80)
    else:
        base_score = random.randint(50, 70)
    
    if category == "Data Structures":
        feedback = "Your understanding of data structures is basic. To improve, provide more specific examples and discuss time/space complexities."
    elif category == "Algorithms":
        feedback = "You explained the concept but need more detail. Add complexity analysis and implementation details."
    elif category == "System Design":
        feedback = "Good high-level thinking. Add more specific components, technologies, and scalability considerations."
    elif category == "Behavioral":
        feedback = "Good personal example. Use the STAR method more clearly and add specific outcomes/metrics."
    else:
        feedback = "Good attempt. Add more technical details and real-world applications."
    
    return {
        "score": base_score,
        "strengths": ["Clear explanation", "Good structure"],
        "improvements": ["Add more examples", "Be more concise"],
        "feedback": feedback
    }

# ========== PAGE FUNCTIONS ==========
def show_practice():
    st.title("📝 Practice Questions")
    
    if not st.session_state.api_configured:
        st.info("ℹ️ **Demo Mode Active** - Using simulated AI responses. Add OpenAI API key to enable real AI features.")
    
    question_options = [f"Q{q['id']}: {q['question'][:50]}..." for q in QUESTIONS]
    selected_index = st.selectbox(
        "Choose a question:",
        range(len(QUESTIONS)),
        format_func=lambda i: question_options[i],
        key="question_selector"
    )
    
    question = QUESTIONS[selected_index]
    qid = str(question['id'])
    
    st.subheader(f"Question {question['id']}: {question['question']}")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"**Category:** {question['category']}")
    with col2:
        st.info(f"**Difficulty:** {question['difficulty']}")
    with col3:
        st.info(f"**Ideal Length:** {question['ideal_length']}")
    
    with st.expander("🔑 Key concepts to cover (click to expand)"):
        cols = st.columns(3)
        for i, keyword in enumerate(question['keywords']):
            cols[i % 3].markdown(f"• **{keyword}**")
    
    # Load existing answer if available
    progress = st.session_state.progress
    existing_answer = progress.get('answers', {}).get(qid, "")
    
    # Initialize session state for this question
    transcript_key = f'audio_transcript_{qid}'
    text_answer_key = f'text_answer_{qid}'
    last_audio_key = f'last_audio_{qid}'
    
    # Initialize session state keys if they don't exist
    if transcript_key not in st.session_state:
        st.session_state[transcript_key] = ""
    if text_answer_key not in st.session_state:
        st.session_state[text_answer_key] = existing_answer
    if last_audio_key not in st.session_state:
        st.session_state[last_audio_key] = None
    
    # Show audio recording section
    st.divider()
    
    if not st.session_state.api_configured:
        st.info("🎤 **Voice recording requires OpenAI API key** to enable voice features.")
    else:
        # Use custom audio recorder component
        audio_recorder_component(question['id'])
        
        # Show transcribe section if we have audio
        if st.session_state[last_audio_key] is not None:
            st.divider()
            st.subheader("🎤 Transcribe Your Audio")
            
            # Audio info
            audio_size = get_audio_size(st.session_state[last_audio_key])
            st.info(f"✅ Audio recorded ({audio_size} KB)")
            
            col_trans1, col_trans2 = st.columns([2, 1])
            
            with col_trans1:
                if st.button("🎤 Transcribe Audio", 
                           key=f"transcribe_btn_{qid}", 
                           use_container_width=True, 
                           type="primary"):
                    with st.spinner("Transcribing audio..."):
                        try:
                            transcript = transcribe_audio(
                                st.session_state[last_audio_key], 
                                question['id']
                            )
                            if transcript:
                                st.session_state[transcript_key] = transcript
                                st.session_state[text_answer_key] = transcript
                                progress['answers'][qid] = transcript
                                st.success("✅ Transcription complete and saved!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Transcription failed: {str(e)[:100]}")
                            demo_transcript = get_question_demo_transcript(question['id'])
                            st.session_state[transcript_key] = demo_transcript
                            st.session_state[text_answer_key] = demo_transcript
                            progress['answers'][qid] = demo_transcript
                            st.info("Using demo transcription. Check your API key and try again.")
                            st.rerun()
            
            with col_trans2:
                if st.button("🗑️ Remove Audio", 
                           key=f"remove_audio_{qid}",
                           help="Remove audio and start over",
                           use_container_width=True):
                    st.session_state[last_audio_key] = None
                    if f'recording_active_{qid}' in st.session_state:
                        st.session_state[f'recording_active_{qid}'] = False
                    st.success("Audio removed. You can record again.")
                    st.rerun()
            
            # Show existing transcript if available
            if st.session_state[transcript_key]:
                st.divider()
                st.subheader("📝 Your Transcribed Answer")
                st.text_area(
                    "Transcribed Text",
                    st.session_state[transcript_key],
                    height=150,
                    key=f"transcript_display_{qid}",
                    disabled=True
                )
    
    # Determine final answer to evaluate
    final_answer = st.session_state.get(text_answer_key, "")
    
    # Save answer to progress when user transcribes
    if final_answer and final_answer != existing_answer:
        progress['answers'][qid] = final_answer
    
    # Word count display
    if final_answer:
        word_count = len(final_answer.split())
        st.caption(f"📊 Word count: {word_count} (Ideal: {question['ideal_length']})")
    
    # EVALUATE BUTTON SECTION
    st.divider()
    st.subheader("📊 Evaluation")
    
    # Check if we need to show evaluation results
    evaluation_key = f'evaluation_{qid}'
    show_evaluation = False
    eval_data = None
    
    # Check if we have existing evaluation in progress
    if qid in progress.get('evaluations', {}):
        show_evaluation = True
        eval_data = progress['evaluations'][qid]
    elif evaluation_key in st.session_state:
        show_evaluation = True
        eval_data = st.session_state[evaluation_key]
        progress['evaluations'][qid] = eval_data
    
    # Show evaluation section
    if final_answer and final_answer.strip():
        word_count = len(final_answer.split())
        st.success(f"✅ **Answer ready for evaluation** ({word_count} words)")
        
        # Evaluation button
        if st.button("✅ Evaluate Answer", 
                    key=f"eval_{qid}", 
                    type="primary", 
                    use_container_width=True):
            with st.spinner("🔍 Analyzing your answer..."):
                progress['answers'][qid] = final_answer
                
                # Get AI evaluation (single score only)
                ai_eval = evaluate_with_gpt(question, final_answer)
                
                # Use the AI score as the overall score
                overall_score = ai_eval['score']
                
                # Update progress
                if qid not in progress['completed']:
                    progress['completed'].append(qid)
                progress['scores'][qid] = overall_score
                
                # Store evaluation details
                eval_data = {
                    'overall_score': overall_score,
                    'word_count': word_count,
                    'feedback': ai_eval
                }
                
                st.session_state[evaluation_key] = eval_data
                progress['evaluations'][qid] = eval_data
                
                show_evaluation = True
                st.success("✅ Evaluation Complete!")
                st.rerun()
        
        # Show evaluation results if available
        if show_evaluation and eval_data:
            st.divider()
            st.subheader("📈 Evaluation Results")
            
            # Show SINGLE score only
            col_score = st.columns(1)
            with col_score[0]:
                score = eval_data['overall_score']
                st.metric("Overall Score", f"{score}%")
                # Show progress bar with score
                progress_value = min(max(score / 100, 0), 1)
                st.progress(progress_value)
                
                # Performance indicator
                if score >= 80:
                    st.success("🎉 Excellent performance!")
                elif score >= 70:
                    st.info("👍 Good performance")
                elif score >= 60:
                    st.warning("⚠️ Needs improvement")
                else:
                    st.error("📝 Requires significant improvement")
            
            # Feedback sections
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                st.subheader("✅ Strengths")
                for strength in eval_data['feedback']['strengths']:
                    st.success(f"• {strength}")
            
            with col_f2:
                st.subheader("📈 Areas for Improvement")
                for improvement in eval_data['feedback']['improvements']:
                    st.warning(f"• {improvement}")
            
            # Detailed feedback
            st.subheader("📝 Detailed Feedback")
            st.info(eval_data['feedback']['feedback'])
    
    else:
        # No answer yet
        st.info("💡 **Record your answer, then transcribe it, and click 'Evaluate Answer'**")
        
        st.button("⏸️ Evaluate Answer (Disabled)", 
                 disabled=True, 
                 use_container_width=True,
                 help="Please record and transcribe your answer first")
    
    # Reset button for this question
    st.divider()
    if st.button("🔄 Reset This Question", 
                key=f"reset_question_full_{qid}", 
                use_container_width=True, 
                type="secondary"):
        if clear_question_data(qid):
            st.success(f"Question {qid} reset successfully!")
            st.rerun()

def show_home():
    st.title("💻 Ai Interview Practice Platform")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ## 🚀 Master Technical Interviews with Voice
        
        **Practice speaking your answers** with AI-powered feedback to ace your next technical interview.
        
        ### Features:
        ✅ **10 Common Interview Questions** across 4 categories  
        ✅ **Voice-Only Answers** - Practice speaking like real interviews  
        ✅ **AI Transcription** - Convert your speech to text  
        ✅ **AI Evaluation** - Get detailed feedback on your answers  
        ✅ **Progress Tracking** - Monitor improvement over time  
        ✅ **PDF Reports** - Download your progress for review  
        
        ### How to Start:
        1. **Choose a question** from the Practice page
        2. **Record your spoken answer**
        3. **Transcribe it to text**
        4. **Get AI feedback** with a single overall score
        
        ### Audio Recording Instructions:
        1. Click **🎤 Start Recording** 
        2. Allow microphone access when prompted
        3. Speak your answer clearly
        4. Click **🎤 Transcribe Audio** to convert to text
        5. Click **✅ Evaluate Answer** to get feedback
        
        **Your progress is automatically saved!** You can return anytime.
        """)
        
        if st.button("🎯 Start Practicing Now", type="primary", use_container_width=True):
            st.session_state.page = "practice"
            st.rerun()
    
    with col2:
        # API Status Card
        if st.session_state.api_configured:
            st.success("### ✅ API Status")
            st.write("**OpenAI API:** Configured")
            st.write("**Mode:** Real AI Mode")
            st.write("**Features Available:**")
            st.write("• 🎤 Real voice transcription")
            st.write("• 🤖 AI evaluation")
            st.write("• 📊 Single score feedback")
        else:
            st.info("### ⚠️ API Status")
            st.write("**OpenAI API:** Not configured")
            st.write("**Mode:** Demo Mode")
            st.write("**Features:** Simulated responses")
            st.write("**To enable real AI:**")
            st.write("1. Get API key from OpenAI")
            st.write("2. Add to Streamlit secrets")
            st.write("3. Deploy to Streamlit Cloud")
        
        st.divider()
        
        # Progress stats
        progress = st.session_state.progress
        attempted = len(progress.get('answers', {}))
        completed = len(progress['completed'])
        
        st.write("**Your Progress:**")
        col_stat1, col_stat2 = st.columns(2)
        with col_stat1:
            st.metric("Attempted", attempted)
        with col_stat2:
            st.metric("Evaluated", completed)
        
        if attempted > 0:
            progress_value = min(max(completed / len(QUESTIONS), 0), 1)
            st.progress(progress_value)
        
        # Quick stats
        if progress['scores']:
            avg_score = sum(progress['scores'].values()) / len(progress['scores'])
            st.write(f"**Average Score:** {avg_score:.1f}%")

def show_dashboard():
    st.title("📊 Progress Dashboard")
    
    progress = st.session_state.progress
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        completed = len(progress['completed'])
        st.metric("Completed", f"{completed}/{len(QUESTIONS)}")
        progress_value = min(max(completed / len(QUESTIONS) if len(QUESTIONS) > 0 else 0, 0), 1)
        st.progress(progress_value)
    
    with col2:
        attempted = len(progress.get('answers', {}))
        st.metric("Attempted", f"{attempted}/{len(QUESTIONS)}")
        progress_value = min(max(attempted / len(QUESTIONS) if len(QUESTIONS) > 0 else 0, 0), 1)
        st.progress(progress_value)
    
    with col3:
        if progress['scores']:
            avg_score = sum(progress['scores'].values()) / len(progress['scores'])
            st.metric("Average Score", f"{avg_score:.1f}%")
        else:
            st.metric("Average Score", "0%")
    
    with col4:
        if progress['completed']:
            last_qid = progress['completed'][-1]
            last_score = progress['scores'].get(last_qid, 0)
            st.metric("Last Score", f"{last_score}%")
        elif progress.get('answers'):
            st.metric("Last Attempt", "Pending")
        else:
            st.metric("Last Score", "N/A")
    
    st.divider()
    st.subheader("📋 Question Status")
    
    # Create a table-like display
    for question in QUESTIONS:
        qid = str(question['id'])
        completed = qid in progress['completed']
        attempted = qid in progress.get('answers', {})
        score = progress['scores'].get(qid, 0)
        
        # Create status indicator
        if completed:
            status = "✅ Completed"
            score_display = f"{score}%"
            status_color = "green"
        elif attempted:
            status = "🎤 Recorded"
            score_display = "Pending"
            status_color = "blue"
        else:
            status = "⏳ Not Attempted"
            score_display = "-"
            status_color = "gray"
        
        # Display in columns
        col1, col2, col3, col4 = st.columns([1, 3, 2, 2])
        
        with col1:
            st.write(f"**Q{qid}**")
        
        with col2:
            st.write(f"{question['question'][:70]}...")
        
        with col3:
            st.markdown(f"<span style='color:{status_color}'>{status}</span>", unsafe_allow_html=True)
        
        with col4:
            if completed:
                st.success(score_display)
            elif attempted:
                st.info(score_display)
            else:
                st.write(score_display)
    
    st.divider()
    
    # Show detailed answer history
    if progress.get('answers'):
        st.subheader("📝 Answer History")
        sorted_qids = sorted(progress['answers'].keys(), 
                           key=lambda x: int(x), 
                           reverse=True)
        
        for qid in sorted_qids[:3]:
            with st.expander(f"Question {qid} - {QUESTIONS[int(qid)-1]['question'][:50]}..."):
                question = QUESTIONS[int(qid)-1]
                st.write(f"**Question:** {question['question']}")
                st.write(f"**Category:** {question['category']} | **Difficulty:** {question['difficulty']}")
                
                answer = progress['answers'][qid]
                st.write(f"**Your Answer:** {answer[:300]}...")
                
                if qid in progress['completed']:
                    score = progress['scores'].get(qid, 0)
                    st.write(f"**Score:** {score}%")
                    
                    if qid in progress.get('evaluations', {}):
                        eval_data = progress['evaluations'][qid]
                        st.write(f"**Word Count:** {eval_data['word_count']}")
                else:
                    st.warning("Answer recorded but not evaluated yet")
        
        if len(progress['answers']) > 3:
            st.info(f"... and {len(progress['answers']) - 3} more answers")
    
    # Quick action buttons
    st.divider()
    col_act1, col_act2, col_act3 = st.columns(3)
    with col_act1:
        if st.button("📝 Practice More", use_container_width=True):
            st.session_state.page = "practice"
            st.rerun()
    
    with col_act2:
        if st.button("📄 Generate Report", use_container_width=True):
            st.session_state.page = "report"
            st.rerun()
    
    with col_act3:
        if st.button("🏠 Go Home", use_container_width=True):
            st.session_state.page = "home"
            st.rerun()

def show_report():
    st.title("📄 Generate Report")
    
    progress = st.session_state.progress
    
    if not progress.get('answers'):
        st.warning("Record at least one answer to generate a report")
        if st.button("📝 Go Practice", use_container_width=True):
            st.session_state.page = "practice"
            st.rerun()
        return
    
    def generate_pdf():
        pdf = FPDF()
        pdf.add_page()
        
        # Title
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Tech Interview Practice Report", 0, 1, 'C')
        pdf.ln(5)
        
        # Date
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1, 'R')
        pdf.ln(10)
        
        # Mode info
        pdf.set_font("Arial", '', 10)
        mode = "Demo Mode" if not st.session_state.api_configured else "Real AI Mode"
        pdf.cell(0, 10, f"Mode: {mode}", 0, 1)
        pdf.ln(5)
        
        # Progress Summary
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Progress Summary", 0, 1)
        pdf.set_font("Arial", '', 12)
        
        completed = len(progress['completed'])
        attempted = len(progress.get('answers', {}))
        pdf.cell(0, 10, f"Total Questions: {len(QUESTIONS)}", 0, 1)
        pdf.cell(0, 10, f"Questions Attempted: {attempted}", 0, 1)
        pdf.cell(0, 10, f"Questions Evaluated: {completed}", 0, 1)
        
        if progress['scores']:
            avg_score = sum(progress['scores'].values()) / len(progress['scores'])
            highest = max(progress['scores'].values()) if progress['scores'] else 0
            lowest = min(progress['scores'].values()) if progress['scores'] else 0
            
            pdf.cell(0, 10, f"Average Score: {avg_score:.1f}%", 0, 1)
            pdf.cell(0, 10, f"Highest Score: {highest}%", 0, 1)
            pdf.cell(0, 10, f"Lowest Score: {lowest}%", 0, 1)
        
        pdf.ln(10)
        
        # Question Details
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Question Details", 0, 1)
        pdf.set_font("Arial", '', 10)
        
        for qid in sorted(progress.get('answers', {}).keys(), key=int):
            question = QUESTIONS[int(qid)-1]
            answer = progress['answers'][qid]
            
            pdf.set_font("Arial", 'B', 11)
            pdf.multi_cell(0, 8, f"Question {qid}: {question['question']}")
            
            pdf.set_font("Arial", 'I', 10)
            if qid in progress['completed']:
                score = progress['scores'].get(qid, 0)
                pdf.cell(0, 8, f"Score: {score}% | Category: {question['category']} | Difficulty: {question['difficulty']}", 0, 1)
            else:
                pdf.cell(0, 8, f"Status: Recorded (Not evaluated) | Category: {question['category']}", 0, 1)
            
            pdf.set_font("Arial", '', 10)
            truncated_answer = answer[:400] + "..." if len(answer) > 400 else answer
            pdf.multi_cell(0, 8, f"Your Answer: {truncated_answer}")
            pdf.ln(5)
        
        # Footer
        pdf.set_font("Arial", 'I', 8)
        pdf.cell(0, 10, "Generated by Tech Interview Practice Platform", 0, 1, 'C')
        
        return pdf.output(dest='S').encode('latin-1')
    
    # Report Preview
    st.subheader("Report Preview")
    
    col1, col2 = st.columns(2)
    
    with col1:
        attempted = len(progress.get('answers', {}))
        completed = len(progress['completed'])
        
        st.metric("Questions Attempted", attempted)
        progress_value = min(max(attempted / len(QUESTIONS), 0), 1)
        st.progress(progress_value)
        
        st.metric("Questions Evaluated", completed)
        progress_value = min(max(completed / len(QUESTIONS), 0), 1)
        st.progress(progress_value)
        
        st.write("**Attempted Questions:**")
        for qid in sorted(progress.get('answers', {}).keys(), key=int):
            question = QUESTIONS[int(qid)-1]
            status = "✅ Evaluated" if qid in progress['completed'] else "🎤 Recorded"
            score_display = f" ({progress['scores'].get(qid, 0)}%)" if qid in progress['completed'] else ""
            st.write(f"• Q{qid}: {question['question'][:40]}... {status}{score_display}")
    
    with col2:
        if progress['scores']:
            avg_score = sum(progress['scores'].values()) / len(progress['scores'])
            highest = max(progress['scores'].values()) if progress['scores'] else 0
            lowest = min(progress['scores'].values()) if progress['scores'] else 0
            
            st.metric("Average Score", f"{avg_score:.1f}%")
            st.metric("Highest Score", f"{highest}%")
            st.metric("Lowest Score", f"{lowest}%")
            
            # Score distribution
            scores_list = list(progress['scores'].values())
            if scores_list:
                st.write("**Score Distribution:**")
                for range_start in range(0, 100, 20):
                    range_end = range_start + 20
                    count = sum(1 for s in scores_list if range_start <= s < range_end)
                    if range_end == 100:
                        count = sum(1 for s in scores_list if s >= 90)
                    st.write(f"{range_start}-{range_end}%: {count} questions")
        elif progress.get('answers'):
            st.info("### 📊 Scores")
            st.write("Complete evaluation to see scores")
            st.write("Click 'Evaluate Answer' on practice questions")
    
    # Mode info
    mode_status = "🚀 Demo Mode (simulated responses)" if not st.session_state.api_configured else "🤖 Real AI Mode (GPT & Whisper APIs)"
    st.info(f"**Current Mode:** {mode_status}")
    
    # PDF Generation
    st.divider()
    st.subheader("Download Report")
    
    if st.button("📥 Generate & Download PDF Report", type="primary", use_container_width=True):
        with st.spinner("Generating PDF report..."):
            pdf_bytes = generate_pdf()
            
            # Create download button
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            st.download_button(
                label="⬇️ Click to Download PDF",
                data=pdf_bytes,
                file_name=f"tech_interview_report_{timestamp}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            
            st.success("✅ Report generated successfully!")

# ========== MAIN APP ==========
def main():
    if 'page' not in st.session_state:
        st.session_state.page = "home"
    
    show_sidebar()
    
    current_page = st.session_state.page
    if current_page == "home":
        show_home()
    elif current_page == "practice":
        show_practice()
    elif current_page == "dashboard":
        show_dashboard()
    elif current_page == "report":
        show_report()

if __name__ == "__main__":
    main()
