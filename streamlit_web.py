"""Web interface"""

import re

import numpy as np
import pandas as pd
from sklearn.manifold import TSNE
import streamlit as st
from textblob import TextBlob

import src.analyzer as az
import src.doc_similarity as ds
import src.markdown as md
import src.summarizer as sz
import src.topic_modeling as tm
import src.visualization as vis


# resources/cs100f2019_lab05_reflections
# resources/combined/lab1, resources/combined/lab2

# initialize main_df and preprocessed_Df
preprocessed_df = pd.DataFrame()
main_df = pd.DataFrame()
directory = None
assignments = None
assign_text = None
stu_id = None


def main():
    """main streamlit function"""
    # Title
    st.sidebar.title("Welcome to TextMining!")
    global directory
    directory = st.sidebar.text_input(
        "Enter path(s) to documents (seperate by comma)")
    if len(directory) == 0:
        st.sidebar.text("Please enter the path to the directory")
        with open("README.md") as readme_file:
            st.markdown(readme_file.read())
    else:
        directory = re.split(r"[;,\s]\s*", directory)
        try:
            global preprocessed_df
            global main_df
            main_df, preprocessed_df = import_data(directory)
            if main_df is not None:
                st.sidebar.success("Sucessfully Loaded!!")
            global assignments
            assignments = st.sidebar.multiselect(
                label="Select assignments below:",
                options=main_df["Assignment"].unique(),
            )
            global assign_text
            assign_text = ", ".join(assignments)
            global stu_id
            stu_id = preprocessed_df.columns[1]
            analysis_mode = st.sidebar.selectbox(
                "Choose the analysis mode",
                [
                    "Home",
                    "Frequency Analysis",
                    "Sentiment Analysis",
                    "Document Similarity",
                    "Summary",
                    "Topic Modeling",
                    "Interactive",
                ],
            )
            if analysis_mode == "Home":
                with open("README.md") as readme_file:
                    st.markdown(readme_file.read())
            if analysis_mode == "Frequency Analysis":
                st.title("Frequency Analysis")
                frequency()
            elif analysis_mode == "Sentiment Analysis":
                st.title("Sentiment Analysis")
                sentiment()
            elif analysis_mode == "Document Similarity":
                st.title("Document Similarity")
                doc_sim()
            elif analysis_mode == "Summary":
                st.title("Summary")
                summary()
            elif analysis_mode == "Topic Modeling":
                st.title("Topic Modeling")
                tpmodel()
            elif analysis_mode == "Interactive":
                st.title("Interactive NLP")
                interactive()
        except FileNotFoundError as err:
            st.sidebar.text(err)
            with open("README.md") as readme_file:
                st.markdown(readme_file.read())


@st.cache(allow_output_mutation=True)
def import_data(paths):
    """import and preprocess data from the paths"""
    tidy_df = pd.DataFrame()
    raw_df = pd.DataFrame()
    for path in paths:
        single_df = pd.DataFrame(md.collect_md(path))
        raw_df = raw_df.append(single_df, ignore_index=True)
        tidy_df = tidy_df.append(df_preprocess(single_df), ignore_index=True)
    return tidy_df, raw_df


def df_preprocess(df):
    """build and preprocess (combine, normalize, tokenize) text"""
    # filter out first two columns -- non-report content
    cols = df.columns[2:]
    # combining text into combined column
    df["combined"] = df[cols].apply(
        lambda row: "\n".join(row.values.astype(str)), axis=1
    )
    # normalize
    df["normalized"] = df["combined"].apply(lambda row: az.normalize(row))
    # tokenize
    df["tokens"] = df["normalized"].apply(lambda row: az.tokenize(row))
    return df


def frequency():
    """main function for frequency analysis"""
    freq_type = st.sidebar.selectbox(
        "Type of frequency analysis", ["Overall", "Student", "Question"]
    )
    if freq_type == "Overall":
        freq_range = st.sidebar.slider(
            "Select a range of Most frequent words", 1, 50, value=25
        )
        st.sidebar.success(
            'To continue see individual frequency analysis select "Student"'
        )
        st.header(f"Overall most frequent words in **{assign_text}**")
        overall_freq(freq_range)
    elif freq_type == "Student":
        freq_range = st.sidebar.slider(
            "Select a range of Most frequent words", 1, 20, value=10
        )
        st.header(
            f"Most frequent words by individual students in **{assign_text}**")
        student_freq(freq_range)
    elif freq_type == "Question":
        freq_range = st.sidebar.slider(
            "Select a range of Most frequent words", 1, 20, value=10
        )
        st.header(
            f"Most frequent words in individual questions in **{assign_text}**"
            )
        question_freq(freq_range)


def overall_freq(freq_range):
    """page fore overall word frequency"""
    plots_range = st.sidebar.slider(
        "Select the number of plots per row", 1, 5, value=3)
    freq_df = pd.DataFrame(columns=["assignment", "word", "freq"])
    # calculate word frequency of each assignments
    for item in assignments:
        # combined text of the whole assignment
        combined_text = " ".join(
            main_df[main_df["Assignment"] == item].normalized)
        item_df = pd.DataFrame(
            az.word_frequency(combined_text, freq_range),
            columns=["word", "freq"]
        )
        item_df["assignment"] = item
        freq_df = freq_df.append(item_df)
    # plot all the subplots of different assignments
    st.altair_chart(
        vis.facet_freq_barplot(
            freq_df, assignments, "assignment", plots_per_row=plots_range
        )
    )


def student_freq(freq_range):
    """page for individual student's word frequency"""
    students = st.multiselect(
        label="Select specific students below:",
        options=main_df[stu_id].unique(),
    )

    plots_range = st.sidebar.slider(
        "Select the number of plots per row", 1, 5, value=3)
    freq_df = pd.DataFrame(columns=["student", "word", "freq"])
    stu_assignment = main_df[
        (main_df[stu_id].isin(students)) & main_df["Assignment"].isin(
            assignments)
    ]
    if len(students) != 0:
        for student in students:
            for item in assignments:
                individual_freq = az.word_frequency(
                    stu_assignment[
                        (stu_assignment["Assignment"] == item)
                        & (stu_assignment[stu_id] == student)
                    ]
                    .loc[:, ["combined"]]
                    .to_string(),
                    freq_range,
                )
                ind_df = pd.DataFrame(
                    individual_freq, columns=["word", "freq"])
                ind_df["assignment"] = item
                ind_df["student"] = student
                freq_df = freq_df.append(ind_df)
        st.altair_chart(
            vis.facet_freq_barplot(
                freq_df,
                students,
                "student",
                color_column="assignment",
                plots_per_row=plots_range,
            )
        )


def question_freq(freq_range):
    """page for individual question's word frequency"""
    # drop columns with all na
    select_preprocess = preprocessed_df[
        preprocessed_df["Assignment"].isin(assignments)
    ].dropna(axis=1, how="all")
    questions = st.multiselect(
        label="Select specific questions below:",
        options=select_preprocess.columns[2:],
    )

    plots_range = st.sidebar.slider(
        "Select the number of plots per row", 1, 5, value=1)

    freq_question_df = pd.DataFrame(columns=["question", "word", "freq"])

    select_text = {}
    for question in questions:
        select_text[question] = main_df[question].to_string(
            index=False, na_rep="")
    question_df = pd.DataFrame(
        select_text.items(), columns=["question", "text"])
    if len(questions) != 0:
        for question in questions:
            quest_freq = az.word_frequency(
                question_df[question_df["question"] == question]
                .loc[:, ["text"]]
                .to_string(),
                freq_range,
            )
            ind_df = pd.DataFrame(quest_freq, columns=["word", "freq"])
            ind_df["question"] = question
            freq_question_df = freq_question_df.append(ind_df)

        st.altair_chart(
            vis.facet_freq_barplot(
                freq_question_df, questions, "question",
                plots_per_row=plots_range,
            )
        )


def sentiment():
    """main function for sentiment analysis"""
    senti_df = main_df.copy(deep=True)
    # calculate overall sentiment from the combined text
    senti_df["sentiment"] = senti_df["combined"].apply(
        lambda x: TextBlob(x).sentiment.polarity
    )
    senti_df = senti_df[senti_df["Assignment"].isin(assignments)]
    senti_type = st.sidebar.selectbox(
        "Type of sentiment analysis", ["Overall", "Student", "Question"]
    )
    if senti_type == "Overall":
        st.sidebar.success(
            'To continue see individual sentiment analysis select "Student"'
        )
        st.header(f"Overall sentiment polarity in **{assign_text}**")
        overall_senti(senti_df)
    elif senti_type == "Student":
        st.header(
            f"View sentiment by individual students in **{assign_text}**")
        student_senti(senti_df)
    elif senti_type == "Question":
        st.header(
            f"View sentiment by individual questions in **{assign_text}**")
        question_senti(senti_df)


def overall_senti(senti_df):
    """page for overall senti"""
    # display line plot when there are multiple assingments
    if len(assignments) > 1:
        st.altair_chart(vis.stu_senti_lineplot(senti_df, stu_id))
    st.altair_chart((vis.senti_combinedplot(senti_df, stu_id)))


def student_senti(input_df):
    """page for display individual student's sentiment"""
    students = st.multiselect(
        label="Select specific students below:",
        options=input_df[stu_id].unique(),
    )
    plots_range = st.sidebar.slider(
        "Select the number of plots per row", 1, 5, value=3)
    df_selected_stu = input_df.loc[input_df[stu_id].isin(students)]
    senti_df = pd.DataFrame(
        df_selected_stu, columns=["Assignment", stu_id, "sentiment"]
    )
    if len(students) != 0:
        st.altair_chart(
            vis.facet_senti_barplot(
                senti_df, students, stu_id, plots_per_row=plots_range
            )
        )
        st.altair_chart(vis.stu_senti_barplot(senti_df, stu_id))


def question_senti(input_df):
    """page for individual question's sentiment"""
    select_preprocess = preprocessed_df[
        preprocessed_df["Assignment"].isin(assignments)
    ].dropna(axis=1, how="all")
    questions = st.multiselect(
        label="Select specific questions below:",
        options=select_preprocess.columns[2:],
    )
    select_text = []
    for column in questions:
        select_text.append(input_df[column].to_string(index=False, na_rep=""))
    questions_senti_df = pd.DataFrame(
        {"questions": questions, "text": select_text})
    # calculate overall sentiment from the combined text
    questions_senti_df["sentiment"] = questions_senti_df["text"].apply(
        lambda x: TextBlob(x).sentiment.polarity
    )
    if len(select_text) != 0:
        st.altair_chart(vis.question_senti_barplot(questions_senti_df))


def summary():
    """Display summarization"""
    for path in directory:
        summary_df = pd.DataFrame(sz.summarizer(path))
        st.write(summary_df)


def tpmodel():
    """Display topic modeling"""
    topic_df = main_df.copy(deep=True)
    tp_type = st.sidebar.selectbox(
        "Type of topic modeling analysis", ["Histogram", "Scatter"]
    )
    topic_range = st.sidebar.slider(
            "Select the amount of topics", 1, 10, value=5)
    word_range = st.sidebar.slider(
        "Select the amount of words per topic", 1, 10, value=5
    )
    # topic_df["topics"] = topic_df["tokens"].apply(
    #     lambda x: tm.topic_model(
    #         x, NUM_TOPICS=topic_range, NUM_WORDS=word_range)
    # )
    overall_topic_df, lda_model, corpus = tm.topic_model(
        topic_df["tokens"].tolist(),
        NUM_TOPICS=topic_range,
        NUM_WORDS=word_range,
    )
    overall_topic_df["Student"] = topic_df[stu_id]
    overall_topic_df["Assignment"] = topic_df["Assignment"]
    # reorder the column
    overall_topic_df = overall_topic_df[
        [
            "Assignment",
            "Student",
            "Dominant_Topic",
            "Topic_Keywords",
            "Text",
            "Perc_Contribution",
        ]
    ]
    if tp_type == "Histogram":
        st.header(f"Overall topics in **{assign_text}**")
        st.write(topic_df)

        st.write(overall_topic_df)
        st.altair_chart(vis.tp_hist_plot(overall_topic_df))
    elif tp_type == "Scatter":

        # topics = lda_model.show_topics(formatted=False)

        topic_weights = []
        for i, row_list in enumerate(lda_model[corpus]):
            topic_weights.append([w for i, w in row_list[0]])

        # Array of topic weights
        arr = pd.DataFrame(topic_weights).fillna(0).values

        # st.write(arr)

        # Keep the well separated points (optional)
        arr = arr[np.amax(arr, axis=1) > 0.35]

        # st.write(arr)

        # Dominant topic number in each doc
        topic_num = np.argmax(arr, axis=1)

        # st.write(topic_num)

        random_state = st.sidebar.slider(
            "Select random_state", 1, 1000, value=500)

        angle = st.sidebar.slider("Select angle", 0, 100, value=50)

        # tSNE Dimension Reduction
        tsne_model = TSNE(
            n_components=2,
            verbose=1,
            random_state=random_state,
            angle=angle / 100,
            init="pca",
        )
        tsne_lda = tsne_model.fit_transform(arr)

        df_tsne = pd.DataFrame(
            {
                "x": tsne_lda[:, 0],
                "y": tsne_lda[:, 1],
                "topic": topic_num,
                "topic_num": overall_topic_df["Dominant_Topic"],
            }
        )
        # df_tsne["topic_num"] = overall_topic_df["Dominant_Topic"]
        # st.write(df_tsne)

        lda_scatter = vis.tp_scatter_plot(df_tsne)
        st.altair_chart(lda_scatter)


def doc_sim():
    """Display document similarity"""
    doc_df = main_df.copy(deep=True)
    doc_sim_type = st.sidebar.selectbox(
        "Type of similarity analysis", ["TF-IDF", "Spacy"]
    )
    st.header(
        f"Similarity between each student's document in **{assign_text}**")
    if doc_sim_type == "TF-IDF":
        tf_idf_sim(doc_df)
    elif doc_sim_type == "Spacy":
        spacy_sim(doc_df)


def tf_idf_sim(doc_df):
    for assignment in assignments:
        doc = doc_df[doc_df["Assignment"] == assignment].dropna(
            axis=1, how="all")

        pairs = ds.create_pair(doc[stu_id])
        # calculate similarity of the docs of the selected author pairs
        similarity = [
            ds.tfidf_cosine_similarity(
                (
                    doc[doc[stu_id] == pair[0]]["normalized"].values[0],
                    doc[doc[stu_id] == pair[1]]["normalized"].values[0],
                )
            )
            for pair in pairs
        ]
        df_sim = pd.DataFrame({"pair": pairs, "similarity": similarity})
        # Split the pair tuple into two columns for plotting
        df_sim[["doc_1", "doc_2"]] = pd.DataFrame(
            df_sim["pair"].tolist(), index=df_sim.index
        )
        st.altair_chart(
            vis.doc_sim_heatmap(df_sim).properties(title=assignment))


def spacy_sim(doc_df):
    for assignment in assignments:
        doc = doc_df[doc_df["Assignment"] == assignment].dropna(
            axis=1, how="all")

        pairs = ds.create_pair(doc[stu_id])
        # calculate similarity of the docs of the selected author pairs
        similarity = [
            ds.spacy_doc_similarity(
                (
                    doc[doc[stu_id] == pair[0]]["normalized"].values[0],
                    doc[doc[stu_id] == pair[1]]["normalized"].values[0],
                )
            )
            for pair in pairs
        ]
        df_sim = pd.DataFrame({"pair": pairs, "similarity": similarity})
        # Split the pair tuple into two columns for plotting
        df_sim[["doc_1", "doc_2"]] = pd.DataFrame(
            df_sim["pair"].tolist(), index=df_sim.index
        )
        st.altair_chart(
            vis.doc_sim_heatmap(df_sim).properties(title=assignment))


def interactive():
    """Page to allow nlp analysis from user input"""
    input_text = st.text_area("Enter text", "Type here")
    token_cb = st.checkbox("Show tokens")
    ner_cb = st.checkbox("Show named entities")
    sentiment_cb = st.checkbox("Show sentiment")
    summary_cb = st.checkbox("Show Summary")
    # if st.button("Analysis"):
    tokens = az.tokenize(input_text)
    named_entities = az.named_entity_recognization(input_text)
    summaries = sz.summarize_text(input_text)
    sentiments = TextBlob(input_text)
    # st.success("Running Analysis")

    if token_cb:
        st.write(tokens)
    if ner_cb:
        st.write(named_entities)
    if sentiment_cb:
        st.write(sentiments.sentiment)
    if summary_cb:
        st.write(summaries)


if __name__ == "__main__":
    main()
