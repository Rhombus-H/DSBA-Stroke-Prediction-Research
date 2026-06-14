import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title='Stroke Dataset Explorer', layout='wide')

# ----------------------------------------------------------------------
# Sidebar: where the API lives
# ----------------------------------------------------------------------
st.sidebar.title('Stroke Dataset Explorer')
API_URL = st.sidebar.text_input('API base URL', 'http://localhost:8000')

try:
    health = requests.get(f'{API_URL}/', timeout=3).json()
    st.sidebar.success(f'Connected — {health['rows']} rows loaded')
except Exception:
    st.sidebar.error('API not reachable. Start it with:\n\n'
                     '`uvicorn api:app --port 8000`')

tab_explore, tab_add, tab_overview = st.tabs(
    ['Explore data', 'Add a patient', 'Overview'])

with tab_explore:
    st.header('Explore the dataset')
    st.write('Filter records, then send the query to the API.')

    c1, c2, c3 = st.columns(3)
    with c1:
        gender = st.selectbox('Gender', ['Any', 'Male', 'Female', 'Other'])
        stroke = st.selectbox('Stroke', ['Any', 'Yes (1)', 'No (0)'])
    with c2:
        age_range = st.slider('Age range', 0, 100, (40, 80))
        hypertension = st.selectbox('Hypertension', ['Any', 'Yes (1)', 'No (0)'])
    with c3:
        smoking = st.selectbox('Smoking status',
                               ['Any', 'never smoked', 'formerly smoked',
                                'smokes', 'Unknown'])
        limit = st.number_input('Max rows', 1, 5000, 100)

    if st.button('Run query', type='primary'):
        params = {'min_age': age_range[0], 'max_age': age_range[1], 'limit': limit}
        if gender != 'Any':
            params['gender'] = gender
        if stroke != 'Any':
            params['stroke'] = 1 if '1' in stroke else 0
        if hypertension != 'Any':
            params['hypertension'] = 1 if '1' in hypertension else 0
        if smoking != 'Any':
            params['smoking_status'] = smoking

        try:
            resp = requests.get(f'{API_URL}/patients', params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            st.success(f'{data['count']} patients match — showing {data['returned']}.')
            if data['results']:
                df = pd.DataFrame(data['results'])
                st.dataframe(df, use_container_width=True, hide_index=True)
                if 'age' in df:
                    st.caption('Age distribution of the returned rows')
                    st.bar_chart(df['age'].value_counts().sort_index())
            else:
                st.info('No rows matched these filters.')
        except Exception as e:
            st.error(f'Request failed: {e}')

with tab_add:
    st.header('Add a new patient')
    st.write('Fill the form and submit to create a new record via the API.')

    with st.form('new_patient'):
        a, b = st.columns(2)
        with a:
            f_gender = st.selectbox('Gender', ['Male', 'Female', 'Other'])
            f_age = st.number_input('Age', 0.0, 120.0, 50.0)
            f_hyp = st.selectbox('Hypertension', [0, 1])
            f_heart = st.selectbox('Heart disease', [0, 1])
            f_married = st.selectbox('Ever married', ['Yes', 'No'])
            f_work = st.selectbox('Work type',
                                  ['Private', 'Self-employed', 'Govt_job',
                                   'children', 'Never_worked'])
        with b:
            f_res = st.selectbox('Residence type', ['Urban', 'Rural'])
            f_glucose = st.number_input('Avg glucose level', 0.0, 400.0, 100.0)
            f_bmi = st.number_input('BMI', 0.0, 100.0, 28.0)
            f_smoke = st.selectbox('Smoking status',
                                   ['never smoked', 'formerly smoked',
                                    'smokes', 'Unknown'])
            f_stroke = st.selectbox('Stroke', [0, 1])

        submitted = st.form_submit_button('Create patient', type='primary')

    if submitted:
        payload = {
            'gender': f_gender, 'age': f_age, 'hypertension': f_hyp,
            'heart_disease': f_heart, 'ever_married': f_married,
            'work_type': f_work, 'Residence_type': f_res,
            'avg_glucose_level': f_glucose, 'bmi': f_bmi,
            'smoking_status': f_smoke, 'stroke': f_stroke,
        }
        try:
            resp = requests.post(f'{API_URL}/patients', json=payload, timeout=10)
            if resp.status_code == 201:
                body = resp.json()
                st.success(f'Created patient #{body['patient']['id']}. '
                           f'Dataset now has {body['total_rows']} rows.')
                st.json(body['patient'])
            else:
                st.error(f'Validation error ({resp.status_code}): {resp.text}')
        except Exception as e:
            st.error(f'Request failed: {e}')

with tab_overview:
    st.header('Dataset overview')
    try:
        s = requests.get(f'{API_URL}/stats', timeout=5).json()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric('Total patients', s['total'])
        m2.metric('Stroke rate', f'{s['stroke_rate_pct']}%')
        m3.metric('Mean age', s['mean_age'])
        m4.metric('Mean glucose', s['mean_glucose'])
        st.subheader('Patients by gender')
        st.bar_chart(pd.Series(s['by_gender']))
    except Exception as e:
        st.error(f'Could not load stats: {e}')
