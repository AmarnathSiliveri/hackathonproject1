import streamlit as st
import spacy
from fuzzywuzzy import fuzz
import pandas as pd
import os
import altair as alt
from datetime import datetime
import plotly.express as px


#streamlit app
st.set_page_config(page_title="ONLINE EXAM PORTSL", page_icon='📰')  # page title
st.markdown('<meta name="viewport" content="width=device-width, initial-scale=1.0">', unsafe_allow_html=True)

# Define CSS styling
page_bg = """
<style>
[data-testid='stAppViewContainer'] {
    background-image: url("https://images.unsplash.com/photo-1617396900799-f4ec2b43c7ae?q=80&w=1170&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D");
    background-size: cover;
}
[data-testid="stHeader"] {
background-color: rgba(0,0,0,0);
}
</style>
"""

# Apply the styling using st.markdown
st.markdown(page_bg, unsafe_allow_html=True)
# Load NLP model for grammar check
nlp = spacy.load('en_core_web_sm')


# --- Helper Functions ---
def save_questions(subject, num_questions, questions, correct_answers, date, session):
    if not os.path.exists(f'data/{subject}'):
        os.makedirs(f'data/{subject}')

    # Save the questions, correct answers, date, and session to a CSV file
    question_data = {
        "Question": questions,
        "Correct Answer": correct_answers,
        "Date": [date] * num_questions,
        "Session": [session] * num_questions
    }
    
    df = pd.DataFrame(question_data)
    df.to_csv(f"data/{subject}/{subject}_questions.csv", index=False)

def save_answers(student_id, subject, answers):
    if not os.path.exists(f'data/{subject}'):
        os.makedirs(f'data/{subject}')
    
    # Save answers to a file specific to the subject
    with open(f"data/{subject}/{student_id}_answers.txt", "w") as f:
        for i, answer in enumerate(answers, 1):
            f.write(f"Q{i}: {answer}\n")

def plagiarism_check(answers, correct_answers):
    plagiarism_results = []
    for answer, correct_answer in zip(answers, correct_answers):
        similarity = fuzz.ratio(answer, correct_answer)
        plagiarism_results.append(similarity)
    return plagiarism_results

def grammar_check(doc):
    errors = [token.text for token in doc if token.pos_ == "X"]
    return len(errors)

def save_performance(student_id, subject, plagiarism_results, grammar_errors, num_questions):
    # Create a dictionary to hold performance data
    result_data = {
        "subject": subject,
        "student": student_id,
    }

    for i in range(num_questions):
        result_data[f'q{i + 1}_plagiarism'] = plagiarism_results[i]
        result_data[f'q{i + 1}_grammar_errors'] = grammar_errors[i]

    # Save student performance data in a separate CSV file for each student
    file_path = f"data/{subject}/{student_id}_performance.csv"
    pd.DataFrame([result_data]).to_csv(file_path, index=False)

    # Update overall plagiarism data
    update_overall_plagiarism(subject, plagiarism_results)

def update_overall_plagiarism(subject, plagiarism_results):
    overall_file_path = f"data/{subject}/overall_plagiarism.csv"
    
    if os.path.exists(overall_file_path):
        overall_data = pd.read_csv(overall_file_path)
    else:
        overall_data = pd.DataFrame(columns=["subject", "total_students", "total_plagiarism_score"])

    total_plagiarism_score = sum(plagiarism_results)
    total_students = overall_data['total_students'].sum() + 1  # Increment for new student
    
    # Check if the subject already exists in the overall_data DataFrame
    if overall_data.empty or overall_data['subject'].iloc[0] != subject:
        new_data = pd.DataFrame({
            "subject": [subject],
            "total_students": [total_students],
            "total_plagiarism_score": [total_plagiarism_score]
        })
        overall_data = pd.concat([overall_data, new_data], ignore_index=True)
    else:
        overall_data.at[0, "total_students"] = total_students
        overall_data.at[0, "total_plagiarism_score"] += total_plagiarism_score

    overall_data.to_csv(overall_file_path, index=False)


# Function to display the dashboard based on selected subject, date, and session
# Function to display the dashboard based on selected subject, date, and session
def display_dashboard(selected_subject, selected_date, selected_session, student_id):
    # Construct file paths
    performance_file_path = f'data/{selected_subject}/{student_id}_performance.csv'
    questions_file_path = f"data/{selected_subject}/{selected_subject}_questions.csv"
    overall_plagiarism_path = f'data/{selected_subject}/overall_plagiarism.csv'
    
    # Handle individual student analytics at the top
    if student_id:
        if os.path.exists(performance_file_path):
            try:
                # Read student performance data
                student_performance_data = pd.read_csv(performance_file_path)
                st.subheader(f"Performance Data for Student {student_id}")
                st.write(student_performance_data)

                # Plagiarism and Grammar errors
                questions = [f'q{i + 1}' for i in range(len(student_performance_data.columns) - 2)]
                plagiarism_scores = [student_performance_data[f'q{i + 1}_plagiarism'][0] for i in range(len(questions))]
                grammar_errors = [student_performance_data[f'q{i + 1}_grammar_errors'][0] for i in range(len(questions))]

                # Bar chart for plagiarism scores
                fig_student = px.bar(x=questions, 
                                     y=plagiarism_scores, 
                                     title=f'Plagiarism Scores for Student {student_id}',
                                     labels={'x': 'Questions', 'y': 'Plagiarism Scores'},
                                     color_discrete_sequence=["blue"])

                # Add grammar errors as a line plot
                fig_student.add_scatter(x=questions, 
                                        y=grammar_errors, 
                                        mode='lines+markers', 
                                        name='Grammar Errors', 
                                        marker=dict(color='orange'))

                st.plotly_chart(fig_student)

                # Pie chart for plagiarism and grammar errors
                errors_data = {'Error Type': ['Plagiarism', 'Grammar Errors'], 
                               'Count': [sum(plagiarism_scores), sum(grammar_errors)]}
                errors_df = pd.DataFrame(errors_data)
                st.subheader("Error Distribution")
                st.plotly_chart(px.pie(errors_df, names='Error Type', values='Count', title='Distribution of Errors'))

            except Exception as e:
                st.write(" ")
        else:
            st.warning(f"No performance data available for student {student_id}.")

    # Check if overall performance data exists
    if os.path.exists(overall_plagiarism_path):
        try:
            # Read overall plagiarism data
            overall_data = pd.read_csv(overall_plagiarism_path)
            st.subheader("Overall Plagiarism Statistics")
            st.write(overall_data)

            # Bar chart for total students and total plagiarism score
            fig_overall = px.bar(overall_data, 
                                 x='subject', 
                                 y=['total_students', 'total_plagiarism_score'], 
                                 title='Total Students and Plagiarism Score by Subject',
                                 labels={'value': 'Count', 'variable': 'Metrics'},
                                 barmode='group',
                                 color_discrete_sequence=["blue", "orange"])
            st.plotly_chart(fig_overall)

        except Exception as e:
            st.error(f"Error reading overall plagiarism data: {e}")
    else:
        st.warning("No overall plagiarism data available.")

    # Check if questions data exists
    if os.path.exists(questions_file_path):
        try:
            # Read questions data
            questions_data = pd.read_csv(questions_file_path, on_bad_lines='skip')
            st.subheader("Questions Data")
            st.write(questions_data)

            # Check for necessary columns to display questions by category
            if 'Category' in questions_data.columns and 'Count' in questions_data.columns:
                # Bar chart for number of questions by category
                questions_bar_chart = px.bar(questions_data, 
                                             x='Category',  
                                             y='Count',     
                                             title='Number of Questions by Category',
                                             labels={'Category': 'Categories', 'Count': 'Number of Questions'})
                st.plotly_chart(questions_bar_chart)

            # Check for question type distribution
            if 'Question Type' in questions_data.columns:
                # Pie chart for question type distribution
                questions_pie_chart = px.pie(questions_data, 
                                             names='Question Type',  
                                             values='Count',        
                                             title='Distribution of Questions by Type')
                st.plotly_chart(questions_pie_chart)

        except Exception as e:
            st.error(f"Error reading questions data: {e}")
    else:
        st.warning("No questions data available.")





# --- Main App ---
st.title("Online Exam Portal")

# Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Faculty Dashboard", "Student Page", "Analytics Dashboard"])

# --- Global Variables ---
if "questions" not in st.session_state:
    st.session_state.questions = []
if "answers" not in st.session_state:
    st.session_state.answers = []
if "subject" not in st.session_state:
    st.session_state.subject = ""
if "date" not in st.session_state:
    st.session_state.date = ""
if "session" not in st.session_state:
    st.session_state.session = ""

if page == "Faculty Dashboard":
    st.header("Faculty Dashboard")

    # Input for Subject, Number of Questions, Date, and Session
    subject = st.text_input("Enter Subject:")
    num_questions = st.number_input("Enter the number of questions:", min_value=1, step=1)
    exam_date = st.date_input("Select Exam Date:")
    session = st.selectbox("Choose Session:", ["Morning", "Afternoon"])

    if subject and num_questions and exam_date and session:
        st.session_state.subject = subject
        st.session_state.date = exam_date.strftime("%Y-%m-%d")
        st.session_state.session = session
        st.session_state.questions = []
        st.session_state.answers = []

        st.write(f"Subject: {subject}")
        st.write(f"Number of Questions: {num_questions}")
        st.write(f"Date: {st.session_state.date}")
        st.write(f"Session: {session}")

        # Input for Questions and Correct Answers
        for i in range(num_questions):
            question = st.text_area(f"Enter Question {i + 1}:")
            correct_answer = st.text_area(f"Enter Correct Answer for Question {i + 1}:")
            st.session_state.questions.append(question)
            st.session_state.answers.append(correct_answer)

        if st.button("Save Questions"):
            save_questions(subject, num_questions, st.session_state.questions, st.session_state.answers, st.session_state.date, st.session_state.session)
            st.success("Questions saved successfully! Students can now answer them.")



elif page == "Student Page":
    if not st.session_state.questions or not st.session_state.subject:
        st.warning("No questions available at the moment. Please check back later.")
    else:
        st.header(f"Submit Your Answers for {st.session_state.subject}")

        with st.form("answer_form"):
            student_id = st.text_input("Enter your Student ID:")
            answers = []
            for i, question in enumerate(st.session_state.questions, 1):
                st.write(f"Q{i}: {question}")
                answer = st.text_area(f"Your Answer for Question {i}")
                answers.append(answer)

            submit_button = st.form_submit_button(label="Submit Answers")

        if submit_button:
            save_answers(student_id, st.session_state.subject, answers)
            st.success("Answers submitted successfully!")

            # Plagiarism Detection
            plagiarism_results = plagiarism_check(answers, st.session_state.answers)

            # NLP Evaluation (Grammar, Coherence)
            grammar_errors = []
            for answer in answers:
                doc = nlp(answer)
                grammar_errors.append(grammar_check(doc))

            # Save performance data
            save_performance(student_id, st.session_state.subject, plagiarism_results, grammar_errors, len(answers))


# Analytics Dashboard
elif page == "Analytics Dashboard":
    st.header("Analytics Dashboard")

    selected_subject = st.selectbox("Select Subject:", [f for f in os.listdir('data') if os.path.isdir(os.path.join('data', f))])
    selected_date = st.date_input("Select Date for Analytics:")
    selected_session = st.selectbox("Select Session:", ["Morning", "Afternoon"])
    
    student_id = st.text_input("Enter Student ID")

    if st.button("Show Analytics"):
        display_dashboard(selected_subject, selected_date.strftime("%Y-%m-%d"), selected_session,student_id)

# --- End of Main App ---

















