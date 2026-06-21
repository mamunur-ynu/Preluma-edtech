ALIASES = {
    "qm": "quantum mechanics",
    "quantum": "quantum mechanics",
    "ml": "machine learning",
    "ai": "artificial intelligence",
    "python": "python programming",
    "cnn": "convolutional neural network",
    "nlp": "natural language processing",
    "dbms": "database management system",
    "os": "operating system",
    "network": "computer network",
}

def concept(definition, kid, example, mistake, exam):
    return {
        "definition": definition,
        "kid": kid,
        "example": example,
        "mistake": mistake,
        "exam": exam,
    }

def make_topic(title, definition, simple, concepts, applications=None, misconceptions=None, questions=None):
    return {
        "title": title,
        "hook": f"{title} becomes easier when students understand the big idea before class.",
        "definition": definition,
        "simple": simple,
        "facts": [
            definition,
            simple,
            f"{title} can be understood better with examples and class questions.",
        ],
        "concepts": concepts,
        "applications": applications or {"class learning": f"{title} helps students prepare for lectures."},
        "misconceptions": misconceptions or [
            f"{title} is not only memorization.",
            "Students should connect the definition with examples.",
            "Online preparation should be checked with teacher notes.",
        ],
        "class_questions": questions or [
            f"What is the simplest definition of {title}?",
            f"Can you give one real example of {title}?",
            f"What is the most important concept in {title}?",
            f"What is a common mistake about {title}?",
            f"How is {title} related to our course?",
        ],
    }

TOPICS = {
    "quantum mechanics": make_topic(
        "Quantum Mechanics",
        "Quantum mechanics is the branch of physics that explains how very small things such as electrons, photons, and atoms behave.",
        "Tiny particles follow special rules that are different from everyday objects.",
        {
            "superposition": concept(
                "Superposition means a quantum system can be described as a combination of possible states before measurement.",
                "It is like a spinning coin before it lands.",
                "An electron can have different possible states until we measure it.",
                "It does not mean big daily objects become magical copies.",
                "Mention possible states, measurement, and probability.",
            ),
            "uncertainty": concept(
                "Uncertainty means some pairs of properties cannot both be known perfectly at the same time.",
                "If one thing becomes very clear, another related thing becomes less clear.",
                "Knowing a particle position very accurately makes momentum less certain.",
                "It is not only because instruments are weak.",
                "Mention the fundamental limit of measurement.",
            ),
        },
        {"quantum computing": "Uses quantum states to process information.", "semiconductors": "Modern electronics depend on quantum behavior."},
    ),
    "machine learning": make_topic(
        "Machine Learning",
        "Machine learning is a field of AI where computers learn patterns from data and use them to make predictions or decisions.",
        "It is like teaching a computer through examples instead of writing every rule by hand.",
        {
            "model": concept(
                "A model is the learned pattern created from training data.",
                "It is the computer's learned recipe for making a guess.",
                "A house-price model may learn from size and location.",
                "A model is not automatically always correct.",
                "Mention training, prediction, and evaluation.",
            ),
            "overfitting": concept(
                "Overfitting happens when a model memorizes training data too much and performs poorly on new data.",
                "It is like memorizing one test but failing when questions change.",
                "A model has high training accuracy but low test accuracy.",
                "High training accuracy alone is not enough.",
                "Mention generalization and test performance.",
            ),
        },
        {"medical prediction": "Predict disease risk.", "recommendation": "Suggest videos, songs, or products."},
    ),
    "python programming": make_topic(
        "Python Programming",
        "Python is a high-level programming language used for data, AI, automation, and web apps.",
        "Python is like writing a clear recipe that a computer can follow step by step.",
        {
            "function": concept("A function is a reusable block of code that performs a task.", "It is like a small machine: give input and get output.", "A function can calculate average marks.", "Code inside a function runs only when called.", "Mention input, process, output, and reuse."),
            "loop": concept("A loop repeats a block of code.", "It tells the computer to do the same action again and again.", "A loop can print all names in a list.", "A loop without stopping condition can run forever.", "Mention repetition and control condition."),
        },
    ),
    "data structures": make_topic(
        "Data Structures",
        "Data structures are ways of storing and organizing data so it can be used efficiently.",
        "It is like choosing the right container for different kinds of information.",
        {
            "stack": concept("A stack follows last-in, first-out order.", "It is like a pile of plates.", "Undo operations often use a stack.", "A stack is not the same as a queue.", "Mention LIFO."),
            "queue": concept("A queue follows first-in, first-out order.", "It is like waiting in line.", "Printer jobs can use a queue.", "Queue order is not random.", "Mention FIFO."),
        },
    ),
    "artificial intelligence": make_topic(
        "Artificial Intelligence",
        "Artificial intelligence is the field of building systems that can learn, reason, perceive, or make decisions.",
        "AI is like a smart helper that can make useful guesses but still needs human checking.",
        {"bias": concept("Bias happens when a system gives unfair or distorted results.", "The computer learns a wrong habit from unfair examples.", "A model trained on limited data may fail for other groups.", "AI results are not always neutral.", "Mention data quality and fairness.")},
    ),
    "convolutional neural network": make_topic(
        "Convolutional Neural Network",
        "A convolutional neural network is a deep learning model mainly used for image and visual pattern recognition.",
        "A CNN first notices small patterns like edges, then combines them into bigger objects.",
        {"filter": concept("A filter is a small matrix that scans an image to detect a pattern.", "It is a tiny window looking for lines or shapes.", "A filter can detect vertical edges.", "A filter is learned, not always manually written.", "Mention scanning and feature detection.")},
    ),
    "natural language processing": make_topic(
        "Natural Language Processing",
        "Natural language processing is a field of AI that helps computers understand, analyze, and generate human language.",
        "NLP teaches computers to read, listen, and reply more usefully.",
        {"token": concept("A token is a small piece of text used by an NLP system.", "A sentence is broken into small pieces.", "Words or subwords can be tokens.", "A token is not always a full word.", "Mention text splitting.")},
    ),
    "statistics": make_topic(
        "Statistics",
        "Statistics is the study of collecting, summarizing, analyzing, and interpreting data.",
        "Statistics helps us understand the story behind many numbers.",
        {"variance": concept("Variance measures how spread out numbers are.", "It shows how far numbers usually are from the average.", "Two classes can have the same average but different spread.", "Variance is not the same as ANOVA.", "Mention deviation from mean.")},
    ),
    "urban water management": make_topic(
        "Urban Water Management",
        "Urban water management is the planning and control of water supply, wastewater, drainage, and flood risk in cities.",
        "A city needs clean water coming in and dirty or rain water going out safely.",
        {"drainage": concept("Drainage removes excess rainwater from urban areas.", "It is the city's way of carrying rainwater away.", "Storm drains reduce street flooding.", "Drainage is not the same as drinking water supply.", "Mention flood prevention.")},
    ),
    "database management system": make_topic("Database Management System", "A database management system is software used to create, manage, and access databases.", "It is like a smart digital filing cabinet.", {"primary key": concept("A primary key uniquely identifies each row.", "It is like a unique ID card.", "Student ID can be a primary key.", "Primary key should not repeat.", "Mention uniqueness.")}),
    "software engineering": make_topic("Software Engineering", "Software engineering is the systematic process of designing, building, testing, and maintaining software.", "It is like building a house, but the house is an app or program.", {"testing": concept("Testing checks whether software works correctly.", "It is checking homework before submission.", "Unit tests check small parts.", "Testing cannot be skipped.", "Mention quality assurance.")}),
    "cybersecurity": make_topic("Cybersecurity", "Cybersecurity is the practice of protecting computers, networks, and data from unauthorized access or damage.", "It is like locking doors for your digital life.", {"phishing": concept("Phishing tricks users into giving sensitive information.", "A fake message tries to steal your password.", "Fake bank emails are examples.", "Real-looking links can still be dangerous.", "Mention social engineering.")}),
    "operating system": make_topic("Operating System", "An operating system is system software that manages computer hardware, software resources, and services for programs.", "It is the manager of the computer.", {"process": concept("A process is a running program.", "It is a program that is currently working.", "A browser running on your computer is a process.", "A process is not the same as a file.", "Mention execution.")}),
    "computer network": make_topic("Computer Network", "A computer network is a group of connected devices that exchange data.", "It is like roads connecting computers.", {"protocol": concept("A protocol is a set of communication rules.", "It is the language rules computers follow.", "HTTP is used for web communication.", "Devices need common rules.", "Mention communication standard.")}),
    "linear regression": make_topic("Linear Regression", "Linear regression is a statistical method that models the relationship between input variables and a continuous output.", "It draws a best-fit line to make predictions.", {"slope": concept("Slope shows how much output changes when input changes.", "It tells how steep the line is.", "More study hours may increase score.", "Slope does not always prove causation.", "Mention rate of change.")}),
    "logistic regression": make_topic("Logistic Regression", "Logistic regression is a classification method used to estimate the probability of a binary outcome.", "It predicts the chance of something being yes or no.", {"sigmoid": concept("Sigmoid maps any number to a value between 0 and 1.", "It turns a score into a probability.", "It can show disease risk probability.", "Probability is not always certainty.", "Mention 0 to 1 output.")}),
    "decision tree": make_topic("Decision Tree", "A decision tree is a machine learning model that splits data using decision rules.", "It is like a flowchart of yes/no questions.", {"node": concept("A node is a decision point or result in a tree.", "It is one question box.", "Is glucose high? can be a node.", "Not every node is final.", "Mention decision point.")}),
    "neural network": make_topic("Neural Network", "A neural network is a machine learning model made of connected layers that transform inputs into outputs.", "It is like many small calculators working together to learn patterns.", {"weight": concept("A weight controls the strength of a connection.", "It says how important an input is.", "Glucose may have strong weight in diabetes prediction.", "Weights are learned during training.", "Mention learned parameter.")}),
    "cloud computing": make_topic("Cloud Computing", "Cloud computing delivers servers, storage, databases, networking, software, and analytics through the internet.", "It is like renting computer power online.", {"scalability": concept("Scalability means handling more users or work.", "The system can grow when more people come.", "Adding more cloud resources during exams.", "Scaling can increase cost.", "Mention growth capacity.")}),

    "reinforcement learning": make_topic(
        "Reinforcement Learning",
        "Reinforcement learning is a type of machine learning where an agent learns by taking actions and receiving rewards or penalties.",
        "It is like training a dog — good actions get treats, bad actions get a correction, and the dog learns over time.",
        {
            "reward": concept("A reward is a signal that tells the agent whether its last action was good or bad.", "It is the score the agent gets after each move.", "A game AI earns points for winning moves.", "Reward is not always immediate — sometimes it comes later.", "Mention feedback signal and delayed reward."),
            "policy": concept("A policy is the strategy the agent uses to decide which action to take.", "It is the rule the agent follows to make choices.", "A chess AI follows a policy to choose the next move.", "A good policy is learned over many trials, not hard-coded.", "Mention learned decision strategy."),
        },
    ),
    "blockchain": make_topic(
        "Blockchain Technology",
        "Blockchain is a distributed digital ledger that records transactions in a chain of blocks secured by cryptography.",
        "It is like a notebook that everyone in the room can read, but no one can secretly erase or change.",
        {
            "block": concept("A block is a container that holds a set of transactions and a link to the previous block.", "It is one page in the shared notebook.", "A Bitcoin block stores recent payment records.", "A block is not a single transaction — it holds many.", "Mention hash link and chain."),
            "decentralisation": concept("Decentralisation means no single person or server controls the system.", "Everyone keeps a copy — no single boss can change the record.", "No bank is needed to confirm a crypto payment.", "Decentralised does not mean unregulated.", "Mention distributed control."),
        },
    ),
    "internet of things": make_topic(
        "Internet of Things",
        "The Internet of Things is a network of physical devices embedded with sensors and software that connect and share data over the internet.",
        "It is everyday objects like fridges or watches that can send and receive information online.",
        {
            "sensor": concept("A sensor is a device that detects physical conditions like temperature, motion, or light.", "It is the eye or nose of the smart device.", "A smart thermostat uses a temperature sensor.", "A sensor measures but does not always act — it just reports.", "Mention data collection from the physical world."),
            "connectivity": concept("Connectivity is the ability of devices to communicate with each other or a server.", "It is the Wi-Fi or Bluetooth that links devices together.", "A smartwatch sends step data to a phone app.", "Connectivity alone does not make a device smart — it also needs software.", "Mention network communication."),
        },
    ),
    "cloud computing": make_topic(
        "Cloud Computing",
        "Cloud computing delivers servers, storage, databases, networking, software, and analytics through the internet on demand.",
        "It is like renting powerful computers online instead of buying your own.",
        {
            "scalability": concept("Scalability means the system can handle more users or data by adding resources quickly.", "The system grows when more people come and shrinks when they leave.", "An exam platform adds servers during peak hours.", "Scaling up is not free — cloud costs increase with usage.", "Mention flexible resource growth."),
            "saas": concept("Software as a Service delivers software through the internet without installation.", "You use the software through a browser — no download needed.", "Google Docs is SaaS — you write online without installing Word.", "SaaS needs internet — it does not work fully offline.", "Mention subscription-based software delivery."),
        },
    ),
    "computer vision": make_topic(
        "Computer Vision",
        "Computer vision is a field of AI that trains computers to interpret and understand visual information from images and video.",
        "It teaches computers to see and understand pictures the way humans do.",
        {
            "image classification": concept("Image classification assigns a label to an entire image.", "The system looks at a photo and says what the main object is.", "A model classifies a photo as cat or dog.", "Classification gives one label — it does not find where the object is.", "Mention category prediction from pixels."),
            "object detection": concept("Object detection finds and locates multiple objects in an image with bounding boxes.", "It not only names things but also draws boxes around them.", "A self-driving car detects pedestrians and traffic lights at once.", "Detection is harder than classification — it needs location too.", "Mention bounding box and localisation."),
        },
    ),
    "big data": make_topic(
        "Big Data",
        "Big data refers to datasets too large or complex for traditional software to process efficiently, requiring specialised tools.",
        "It is information so huge that normal spreadsheets cannot handle it — you need special systems.",
        {
            "volume": concept("Volume refers to the massive size of big data — terabytes or petabytes.", "It is so much data that a single computer cannot store it.", "Social media generates millions of posts per hour.", "Volume alone does not make data valuable — quality matters too.", "Mention scale of data storage."),
            "hadoop": concept("Hadoop is an open-source framework for storing and processing large datasets across many computers.", "It splits the data across many machines and processes it in parallel.", "Companies like Yahoo use Hadoop to process web log data.", "Hadoop is not the only big data tool — Spark is faster for some tasks.", "Mention distributed storage and MapReduce."),
        },
    ),
    "api development": make_topic(
        "API Development",
        "An API is an interface that allows two software applications to communicate and share data with each other.",
        "It is a waiter in a restaurant — you give the order, the waiter goes to the kitchen, and brings back the food.",
        {
            "rest api": concept("A REST API uses HTTP methods like GET, POST, PUT, and DELETE to manage resources.", "It follows simple rules for how programs ask each other for data.", "A weather app uses a REST API to get today's temperature.", "REST is not the only API style — GraphQL and gRPC also exist.", "Mention HTTP methods and stateless communication."),
            "endpoint": concept("An endpoint is a specific URL where an API can be accessed.", "It is the exact address where you send your request.", "/users/profile is an endpoint that returns user data.", "Each endpoint does a specific job — not all requests go to the same place.", "Mention URL and resource path."),
        },
    ),
    "devops": make_topic(
        "DevOps",
        "DevOps is a set of practices that combine software development and IT operations to shorten the development cycle and deliver software reliably.",
        "It is developers and operations teams working together instead of separately, using automation to release faster.",
        {
            "ci cd": concept("CI/CD means Continuous Integration and Continuous Deployment — code is tested and released automatically.", "Every time a developer saves code, tests run automatically and the update goes live if they pass.", "A team pushing to GitHub triggers automatic tests and deployment.", "CI/CD does not remove bugs — it finds them faster.", "Mention automated testing and deployment pipeline."),
            "docker": concept("Docker packages an application and its environment into a container that runs the same everywhere.", "It is a box that holds the app and everything it needs to run.", "A Python app in a Docker container runs the same on any computer.", "Docker is not a virtual machine — it shares the host OS kernel.", "Mention containerisation and portability."),
        },
    ),
    "algorithms and complexity": make_topic(
        "Algorithms and Complexity",
        "Algorithm complexity measures how much time and memory an algorithm uses as the input size grows.",
        "It answers: if the input doubles, does the algorithm take twice as long or a hundred times longer?",
        {
            "time complexity": concept("Time complexity measures how the running time of an algorithm grows with input size.", "It tells you how many steps the algorithm needs as data gets bigger.", "Linear search on 1000 items needs 1000 steps — O(n).", "Faster complexity does not always mean faster in practice for small inputs.", "Mention Big-O notation and growth rate."),
            "space complexity": concept("Space complexity measures the memory an algorithm uses as input size grows.", "It tells you how much RAM the algorithm needs.", "Storing all elements in a list needs O(n) space.", "Low time complexity sometimes trades off for higher space complexity.", "Mention memory usage and Big-O."),
        },
    ),
    "quantum computing": make_topic(
        "Quantum Computing",
        "Quantum computing uses quantum mechanics principles like superposition and entanglement to process information in fundamentally new ways.",
        "A normal computer uses 0 or 1. A quantum computer can be 0 and 1 at the same time — doing many calculations at once.",
        {
            "qubit": concept("A qubit is the basic unit of quantum information — it can be 0, 1, or both at the same time.", "It is a coin that is heads and tails until you look at it.", "A quantum computer with 10 qubits can represent 1024 states at once.", "A qubit is not stable — errors happen easily without correction.", "Mention superposition and quantum state."),
            "superposition": concept("Superposition means a qubit can exist in multiple states simultaneously until measured.", "It is the ability to be in two places at once until someone checks.", "Quantum algorithms exploit superposition to check many solutions simultaneously.", "Superposition collapses to one value when measured.", "Mention quantum parallelism."),
        },
    ),
}

def canonical_key(topic: str) -> str:
    key = " ".join(str(topic).strip().lower().split())
    return ALIASES.get(key, key)

def validate_topics():
    errors = []
    required = ["title", "hook", "definition", "simple", "concepts", "applications", "misconceptions", "class_questions"]
    for key, topic in TOPICS.items():
        for field in required:
            if field not in topic or not topic[field]:
                errors.append(f"{key}: missing {field}")
        for cname, c in topic.get("concepts", {}).items():
            for field in ["definition", "kid", "example", "mistake", "exam"]:
                if field not in c or not c[field]:
                    errors.append(f"{key}.{cname}: missing {field}")
    return errors

def _build_topic_options():
    titles = []
    for item in TOPICS.values():
        if isinstance(item, dict) and item.get("title"):
            titles.append(item["title"])
    return sorted(set(titles)) + ["Custom Topic"]

TOPIC_OPTIONS = _build_topic_options()
