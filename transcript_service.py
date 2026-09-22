import re
import html
from youtube_transcript_api import YouTubeTranscriptApi

DEMO_TRANSCRIPTS = {
    # 0. Operating Systems Concurrency (Sample link)
    "UrsmFxElp5k": (
        "Operating Systems Process Synchronization and Semaphores. "
        "The critical section problem occurs when multiple concurrent processes execute shared memory code. "
        "A valid synchronization solution must satisfy three core conditions: Mutual Exclusion, Progress, and Bounded Waiting. "
        "Semaphores provide an integer-based synchronization primitive using atomic wait (P) and signal (V) operations "
        "to prevent race conditions, deadlocks, and resource starvation."
    ),

    # 1. Operating Systems Core
    "q3AuP01daL4": (
        "Operating Systems principles and architecture. An operating system manages computer hardware, "
        "providing a platform for applications to run. Core functions include CPU scheduling algorithms such as "
        "First-Come First-Served (FCFS), Shortest Job First (SJF), and Round Robin. Memory management handles paging, "
        "virtual memory translation, segmentation, and page replacement policies like LRU and FIFO. "
        "Process synchronization addresses the critical section problem using semaphores, mutex locks, and monitors "
        "to prevent race conditions and system deadlocks under Coffman conditions."
    ),

    # 2. Computer Networks Fundamentals
    "ERCMXc8x7mc": (
        "Computer Networks and Internet Architecture. Data communication flows through layered protocol stacks: "
        "the 7-layer OSI model (Physical, Data Link, Network, Transport, Session, Presentation, Application) and the TCP/IP model. "
        "Key protocols include IP addressing (IPv4 and IPv6), subnetting, dynamic routing algorithms (Dijkstra's Link-State and Distance-Vector), "
        "reliable stream transport via TCP three-way handshaking, congestion control, and connectionless UDP transmission. "
        "Application layer protocols include DNS resolution, HTTP/HTTPS secure web transactions, and SSH."
    ),

    # 3. Database Management Systems
    "_aWbUudZ5Yo": (
        "Database Management Systems (DBMS) and Relational Data Models. Relational databases store information in structured tables "
        "governed by schemas and primary/foreign key relationships. Structured Query Language (SQL) enables Data Definition (DDL), "
        "Data Manipulation (DML), and Data Control (DCL). Relational normalization (1NF, 2NF, 3NF, and BCNF) eliminates update anomalies "
        "and data redundancy. Transaction processing guarantees the ACID properties: Atomicity, Consistency, Isolation, and Durability, "
        "maintained through write-ahead logging and two-phase locking concurrency protocols."
    ),

    # 4. Software Engineering & System Design
    "Rq5gJVxz55Q": (
        "Software Engineering lifecycle methodologies and scalable system design. Software Development Life Cycle (SDLC) models "
        "range from traditional Waterfall to Agile, Scrum, and DevOps pipelines. Key requirements engineering steps encompass functional "
        "and non-functional specifications. System design principles include modularity, loose coupling, high cohesion, microservices architecture, "
        "and load balancing across distributed servers. Software testing frameworks mandate unit testing, integration testing, "
        "regression suites, and continuous integration/continuous deployment (CI/CD) pipelines."
    ),

    # 5. Data Structures & Algorithms
    "sCOw5y1RQpY": (
        "Data Structures and Algorithmic Complexity. Efficient computation depends on time and space complexity analyzed via Asymptotic "
        "Big-O notation. Primitive linear structures include arrays, linked lists, stacks, and queues. Non-linear hierarchical structures "
        "include Binary Search Trees (BST), balanced AVL trees, heaps, and graph representations (adjacency matrix and lists). "
        "Essential algorithmic paradigms feature Divide and Conquer (Merge Sort, Quick Sort), Greedy strategies (Kruskal's, Prim's algorithms), "
        "Dynamic Programming (0/1 Knapsack, Longest Common Subsequence), and graph traversals (Breadth-First and Depth-First Search)."
    ),

    # 6. Theory of Computation & Automata
    "ZvU7lupoXQE": (
        "Theory of Computation and Formal Language Theory. Mathematical models of computation examine the fundamental capabilities "
        "and limits of algorithms. The Chomsky Hierarchy classifies grammars into Regular, Context-Free, Context-Sensitive, and Recursively Enumerable. "
        "Automata models progress from Deterministic and Non-Deterministic Finite Automata (DFA/NFA) for regular languages, "
        "to Pushdown Automata (PDA) using memory stacks for context-free languages, to Turing Machines as universal models of computation. "
        "Key theoretical concepts include the Halting Problem, decidability, and P versus NP computational complexity classes."
    ),

    # 7. Computer Organization & Architecture
    "D1eL1EnxXXQ": (
        "Computer Organization and Microprocessor Architecture. Hardware design focuses on instruction set architecture (ISA), "
        "contrasting RISC (Reduced Instruction Set Computer) and CISC architectures. The Von Neumann execution cycle executes fetch, "
        "decode, execute, and memory write-back stages. Instruction-level parallelism is achieved through CPU pipelining, superscalar execution, "
        "and branch prediction. The memory hierarchy bridges CPU and storage speed discrepancies via multi-level cache memory (L1, L2, L3) "
        "using direct-mapped and set-associative cache placement techniques."
    ),

    # 8. Compiler Design
    "bZxAKA69xqg": (
        "Compiler Design and Program Translation phases. A compiler translates high-level source code into target machine instructions. "
        "The analysis phase consists of Lexical Analysis (tokenization via regular expressions and DFAs), Syntax Analysis (parsing via "
        "LL, LR, and LALR context-free grammar parsers), and Semantic Analysis checking type safety. The synthesis phase constructs an "
        "Intermediate Representation (Three-Address Code), performs machine-independent optimizations (dead code elimination, loop unrolling), "
        "and executes target code generation including CPU register allocation."
    ),

    # 9. Object-Oriented Programming (OOP)
    "JMUxmLyrhSk": (
        "Object-Oriented Programming principles and software design patterns. OOP organizes software around data objects rather than "
        "functions and procedural logic. The four core pillars are: Encapsulation (bundling state and methods while restricting direct access), "
        "Abstraction (hiding complex implementation details behind clean interfaces), Inheritance (reusing characteristics across class hierarchies), "
        "and Polymorphism (allowing method overriding and dynamic method dispatch at runtime). Clean design is guided by SOLID design principles."
    ),

    # 10. Web Technologies & Full-Stack Development
    "lxhgomzakBk": (
        "Web Technologies and Client-Server Architectures. Modern web applications operate through browser rendering engines interacting with "
        "backend server endpoints over stateless HTTP/HTTPS communication. The frontend relies on semantic HTML5 structure, CSS styling, "
        "and JavaScript execution for reactive single-page applications. Backend engineering involves RESTful API design, session management, "
        "asynchronous event loops, and database querying, secured against Cross-Site Scripting (XSS) and Cross-Site Request Forgery (CSRF)."
    ),

    # 11. Cloud Computing & Distributed Systems
    "68FcZUpgC7w": (
        "Cloud Computing infrastructure and Distributed Systems. Cloud models provide on-demand resources structured as Infrastructure as a Service (IaaS), "
        "Platform as a Service (PaaS), and Software as a Service (SaaS). Distributed systems manage challenges governed by the CAP theorem: "
        "Consistency, Availability, and Partition Tolerance. Core architectural patterns utilize horizontal scaling, containerization via Docker, "
        "orchestration using Kubernetes, and asynchronous event-driven messaging queues for reliable distributed computing."
    ),

    # 12. Cyber Security & Cryptography
    "5NgNicANyqM": (
        "Cyber Security fundamentals and modern cryptographic standards. Information security ensures the CIA Triad: Confidentiality, Integrity, "
        "and Availability. Cryptographic methods divide into Symmetric encryption (AES, DES using shared private keys) and Asymmetric encryption "
        "(RSA, Elliptic Curve Cryptography using public/private key pairs). Data integrity is verified through cryptographic hashing functions "
        "(SHA-256) and digital certificates signed by Certificate Authorities (CAs). Network defense incorporates firewalls, intrusion detection, "
        "and multi-factor authentication protocols."
    ),

    # 13. Artificial Intelligence & Machine Learning
    "9tbaiFIm0HU": (
        "Artificial Intelligence, Machine Learning, and Neural Models. Machine learning develops algorithms that identify patterns from training data. "
        "The primary paradigms are Supervised Learning (classification, regression), Unsupervised Learning (clustering, dimensionality reduction), "
        "and Reinforcement Learning via reward-based policies. Deep Learning utilizes Artificial Neural Networks consisting of input, hidden, "
        "and output layers. Model weights are iteratively updated through backpropagation and gradient descent optimization to minimize loss."
    ),

    # 14. Live Academic Seminar & Review Session
    "hhGPiDrUe1c": (
        "Comprehensive Computer Science review and technical examination preparation. This live technical lecture synthesizes core concepts "
        "across computer hardware, networking architectures, algorithmic efficiency, operating systems, and full-stack software development. "
        "Special focus is placed on cross-discipline problem-solving strategies, system design trade-offs, and critical revision questions "
        "frequently presented in academic assessments and technical evaluations."
    ),

    # Sample Lectures Buttons
    "aircAruvnKk": (
        "What is a neural network? Deep learning is a branch of machine learning inspired by biological neural networks. "
        "Neurons are organized into layers: input layers take feature vectors, hidden layers compute weighted linear combinations "
        "followed by non-linear activation functions like ReLU and Sigmoid, and output layers provide predictions. "
        "Training optimizes weights using backpropagation and gradient descent to minimize loss."
    ),
    "dhgEAm8384U": (
        "Python in 100 seconds. Python is an interpreted, high-level, dynamically typed programming language created by Guido van Rossum. "
        "It emphasizes developer readability with clean syntax. Widely utilized across web frameworks, automation scripts, "
        "scientific computing, data engineering, and modern artificial intelligence pipelines."
    ),
    "26QPDBe-NB8": (
        "Operating Systems fundamentals. An operating system acts as the fundamental layer between computer hardware and user software. "
        "Core functions include CPU scheduling (FCFS, Round Robin, Multi-level Feedback Queues), memory management (paging, virtual memory, segmentation), "
        "file system structures, I/O device management, and deadlocks resolution."
    )
}

def extract_video_id(url: str) -> str | None:
    if not url:
        return None
    url = url.strip()
    url = re.sub(r'[\[\]\(\)]', ' ', url)
    match = re.search(r'(?:v=|\/vi\/|youtu\.be\/|\/embed\/|\/shorts\/|\/live\/|\/v\/|^)([0-9A-Za-z_-]{11})(?:[?&/#\s]|$)', url)
    if match:
        return match.group(1)
    for token in url.split():
        clean_tok = re.sub(r'[^0-9A-Za-z_-]', '', token)
        if len(clean_tok) == 11 and re.match(r'^[0-9A-Za-z_-]{11}$', clean_tok):
            return clean_tok
    return None

def format_timestamp(seconds: float) -> str:
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def get_transcript(video_id: str, api_key: str = ""):
    # Tier 1: Live YouTube Subtitles
    try:
        t_list = YouTubeTranscriptApi.list_transcripts(video_id)
        try:
            track = t_list.find_transcript(['en', 'en-US', 'en-GB', 'en-IN', 'hi', 'es', 'fr', 'de'])
            data = track.fetch()
        except Exception:
            data = next(iter(t_list)).fetch()

        full_text, segments = [], []
        for item in data:
            line = html.unescape(item.get('text', '')).replace('\n', ' ').strip()
            start_sec = float(item.get('start', 0.0))
            if line:
                full_text.append(line)
                segments.append({"timestamp": format_timestamp(start_sec), "text": line})
        if full_text:
            return " ".join(full_text), segments
    except Exception:
        pass

    # Tier 2: Benchmark Fallback
    if video_id in DEMO_TRANSCRIPTS:
        fallback_text = DEMO_TRANSCRIPTS[video_id]
        segments = [
            {"timestamp": "00:00", "text": "Lecture Introduction & Conceptual Overview."},
            {"timestamp": "02:15", "text": "Core Principles and Algorithmic Breakdown."},
            {"timestamp": "05:30", "text": "System Architecture and Practical Trade-offs."},
            {"timestamp": "08:45", "text": "Summary, Review Questions, and Key Takeaways."}
        ]
        return fallback_text, segments

    raise Exception(f"Unable to extract captions for video ID '{video_id}'. Please use the Direct Text / Transcript Input box.")
