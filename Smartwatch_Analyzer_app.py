import pandas as pd
import numpy as np
import re
import spacy
from flask import Flask, request, render_template
import os

#load_the_spaCy_model
nlp=spacy.load('en_core_web_sm')

#Function:get_data_to_load_review_data_from_csv_file
def get_data(path):
    try:
        review_df=pd.read_csv(path, delimiter=',')
        return review_df
    except FileNotFoundError:
        print(f"Error:The File Path {path} was not found")
        return None
    except pd.errors.ParserError as e:
        print(f"Error parsing the CSV file: {str(e)}")
        return None

#Function_to_dervice_extra_columns_Extract_brand_name_and_product_name_from_review_column_and_generate_keywords_from_review_text
def derive_additional_columns(review_df):
    def extra_info(review):
        #Extra_brand_and_product_using_regular_expressions
        brand_pattern = r"Brand:([A-Za-z0-9\s]+)"
        product_pattern = r"Product: ([A-Za-z0-9\s]+)"
        brand_match = re.search(brand_pattern, review)
        product_match = re.search(product_pattern, review)
        brand_name = brand_match.group(1) if brand_match else "Unknown"
        product_name = product_match.group(1) if product_match else "Unknown"
        return brand_name, product_name
    
    def extract_keywords(review):
        #spacy_to_tokenize_lemmatize_and_remove_stop_words
        doc=nlp(review)
        keywords=[token.lemma_ for token in doc if not token.is_stop and token.pos_ in ["ADJ", "NOUN", "VERB", "ADV"]]
        return ', '.join(keywords)
    
    #apply_extraction_functions_to_the_review_column
    review_df[['Brand Name', 'Product Name']]=review_df['Review'].apply(lambda x:pd.Series(extra_info(x)))
    review_df['Keywords']=review_df['Review'].apply(lambda x:extract_keywords(x))
    return review_df

#Fn.to_filter_the_DataFrame_for_reviews_containing_keyword_&_have_rating_above_threshold_calculate_avg._rating_no._of_platforms,_no._of_reviews_&_unique_keywords
def get_brand_review_summary(review_df, keyword, rating_threshold):
    #filter_reviews_by_keyword_and_rating_threshold
    filtered_df=review_df[(review_df['Keywords'].str.contains(keyword, case=False)) & (review_df['Rating']>rating_threshold)]
    if filtered_df.empty:
        return "No matching Records"
    
    #calculate_summary_statistics
    avg_rating=filtered_df['Rating'].mean()
    platforms_with_reviews=filtered_df['Platform'].nunique()
    num_reviews=filtered_df.shape[0]
    unique_keywords=', '.join(filtered_df['Keywords'].unique())

    #create_summary_dataframe
    summary_df=pd.DataFrame({
        'Brand Name' : [filtered_df['Brand Name'].iloc[0]],
        'Product Name' : [filtered_df['Product Name'].iloc[0]],
        'Avg Rating':[avg_rating],
        'Platforms with reviews':[platforms_with_reviews],
        'Number of Reviews':[num_reviews],
        'Unique Keywords in Reviews':[unique_keywords] 
    })
    return summary_df

#flask_app_for_deployment
app=Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    #get_user_inputs
    file=request.files['file']
    keyword=request.form['keyword']
    rating_threshold=int(request.form['rating_threshold'])

    #save_uploaded_file
    file_path=os.path.join('uploads', file.filename)
    file.save(file_path)

    #load_and_process_data
    review_df=get_data(file_path)
    try:
        if review_df is not None:
            review_df = derive_additional_columns(review_df)
            summary_df = get_brand_review_summary(review_df, keyword=keyword, rating_threshold=rating_threshold)
            return render_template('result.html', tables=[summary_df.to_html(classes='data')], keyword=keyword)
        else:
            return "Error: Could not load data. Please check the CSV file format."
    except KeyError as e:
        return f"Error: {str(e)}"
    
if __name__=="__main__":
    if not os.path.exists('uploads'):
        os.makedirs('uploads')
    #run_flask_app
    app.run(debug=True)


