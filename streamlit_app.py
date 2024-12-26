import streamlit as st
import requests
from datetime import datetime
import pandas as pd
from collections import Counter

st.set_page_config(page_title="Explorador datos.gob.es", layout="wide")

BASE_URL = "http://datos.gob.es/apidata"

def format_title(title_list):
    if not title_list:
        return "Sin título"
    return title_list[0].get('_value', 'Sin título')

def format_date(date_str):
    try:
        dt = datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %Z%z')
        return dt.strftime('%d/%m/%Y %H:%M')
    except:
        return date_str

def get_distribution_urls(dataset_id):
    try:
        response = requests.get(f"{BASE_URL}/catalog/distribution/dataset/{dataset_id}")
        if response.status_code == 200:
            data = response.json()
            return [dist.get('accessURL', '') for dist in data.get('result', {}).get('items', [])]
    except:
        return []

def make_api_request(endpoint, params=None):
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.get(url, params=params)
        return response.json() if response.status_code == 200 else None
    except Exception as e:
        st.error(f"Error API: {str(e)}")
        return None

def get_dataset_stats(data):
    if not data or 'result' not in data or 'items' not in data['result']:
        return {
            'total_datasets': 0,
            'unique_formats': 0,
            'unique_publishers': 0,
            'common_keywords': {},
            'date_range': 'N/A'
        }
    
    items = data['result']['items']
    formats = []
    publishers = []
    keywords = []
    dates = []
    
    for item in items:
        # Procesar distribuciones y formatos
        distributions = item.get('distribution', [])
        if distributions:
            if isinstance(distributions, list):
                for dist in distributions:
                    if isinstance(dist, dict) and 'format' in dist:
                        formats.append(str(dist['format']))
            elif isinstance(distributions, str):
                formats.append(distributions)
        
        # Procesar resto de campos
        if 'publisher' in item:
            publishers.append(str(item['publisher']))
        
        if 'keyword' in item and isinstance(item['keyword'], list):
            keywords.extend([k.get('_value', '') for k in item['keyword'] if isinstance(k, dict)])
        
        if 'issued' in item:
            try:
                dates.append(format_date(item['issued']))
            except:
                pass
    
    return {
        'total_datasets': len(items),
        'unique_formats': len(set(formats)),
        'unique_publishers': len(set(publishers)) if publishers else 0,
        'common_keywords': dict(Counter(keywords).most_common(5)),
        'date_range': f"{min(dates, default='N/A')} - {max(dates, default='N/A')}"
    }

def display_dataset_results(data):
    if data and "result" in data and "items" in data["result"]:
        stats = get_dataset_stats(data)
        
        metric_cols = st.columns(4)
        metric_cols[0].metric("Total Datasets", stats['total_datasets'])
        metric_cols[1].metric("Formatos Únicos", stats['unique_formats'])
        metric_cols[2].metric("Publicadores", stats['unique_publishers'])
        
        if stats['common_keywords']:
            st.subheader("Palabras clave más comunes")
            keyword_cols = st.columns(len(stats['common_keywords']))
            for i, (kw, count) in enumerate(stats['common_keywords'].items()):
                keyword_cols[i].metric(kw, count)
        
        st.divider()
        
        for item in data["result"]["items"]:
            with st.container():
                st.markdown(f"### {format_title(item.get('title', []))}")
                
                col1, col2 = st.columns([2,1])
                with col1:
                    if item.get('publisher'):
                        st.markdown(f"**Publicador:** {item['publisher']}")
                    
                    identifier = item.get('identifier', '')
                    dataset_id = identifier.split('/')[-1]
                    
                    # Mostrar URL del conjunto de datos
                    st.markdown("**🔗 Acceso a los datos:**")
                    st.markdown(f"[Ver en datos.gob.es]({identifier})")
                    
                    # Mostrar URLs de distribuciones
                    urls = get_distribution_urls(dataset_id)
                    if urls:
                        st.markdown("**📊 Descargar datos:**")
                        for url in urls:
                            st.markdown(f"- [{url}]({url})")
                
                with col2:
                    if item.get('issued'):
                        st.markdown(f"**Fecha:** {format_date(item['issued'])}")
                
                if item.get('description'):
                    with st.expander("Ver descripción"):
                        st.write(format_title(item.get('description', [])))
                
                if item.get('keyword'):
                    st.markdown("**Etiquetas:** " + ", ".join([kw.get('_value', '') for kw in item['keyword']]))
                
                st.divider()
    else:
        st.warning("No se encontraron resultados")

def main():
    st.title("🔍 Explorador datos.gob.es")
    
    with st.sidebar:
        st.header("Navegación")
        section = st.selectbox(
            "Sección",
            ["Dataset", "Distribution", "NTI Geographical Coverage", 
             "NTI Primary Sector", "Publisher", "Spatial", "Theme"],
            help="Selecciona la sección principal que deseas explorar"
        )
    
    if section == "Dataset":
        dataset_operation = st.sidebar.selectbox(
            "Operación",
            ["Lista completa", "Buscar por ID", "Buscar por título", "Buscar por publicador",
             "Buscar por tema", "Buscar por formato", "Buscar por palabra clave",
             "Buscar por ubicación", "Buscar por fecha de modificación"],
            help="Selecciona el tipo de búsqueda que deseas realizar"
        )
        
        with st.sidebar:
            st.subheader("Configuración de resultados")
            params = {
                "_pageSize": st.number_input("Resultados por página", 1, 50, 10, 
                                           help="Número de resultados a mostrar por página"),
                "_page": st.number_input("Página", 0, 100, 0,
                                       help="Número de página actual"),
                "_sort": st.selectbox("Ordenar por", 
                                    ["-issued", "title", "-title"],
                                    help="Criterio de ordenación de los resultados")
            }

        # Campos de búsqueda específicos según la operación
        if dataset_operation == "Buscar por ID":
            dataset_id = st.text_input("ID del dataset", help="Introduce el identificador único del dataset")
            if dataset_id and st.button("Buscar", type="primary"):
                data = make_api_request(f"/catalog/dataset/{dataset_id}")
                display_dataset_results(data)

        elif dataset_operation == "Buscar por título":
            title = st.text_input("Título", help="Introduce el título o parte del título a buscar")
            if title and st.button("Buscar", type="primary"):
                data = make_api_request(f"/catalog/dataset/title/{title}", params)
                display_dataset_results(data)

        elif dataset_operation == "Buscar por publicador":
            publisher_id = st.text_input("ID del publicador", help="Introduce el ID del publicador")
            if publisher_id and st.button("Buscar", type="primary"):
                data = make_api_request(f"/catalog/dataset/publisher/{publisher_id}", params)
                display_dataset_results(data)

        elif dataset_operation == "Buscar por tema":
            theme = st.text_input("Tema", help="Introduce el tema a buscar")
            if theme and st.button("Buscar", type="primary"):
                data = make_api_request(f"/catalog/dataset/theme/{theme}", params)
                display_dataset_results(data)

        elif dataset_operation == "Buscar por formato":
            format_type = st.text_input("Formato", help="Introduce el formato (ej: csv, json, xml)")
            if format_type and st.button("Buscar", type="primary"):
                data = make_api_request(f"/catalog/dataset/format/{format_type}", params)
                display_dataset_results(data)

        elif dataset_operation == "Buscar por palabra clave":
            keyword = st.text_input("Palabra clave", help="Introduce la palabra clave a buscar")
            if keyword and st.button("Buscar", type="primary"):
                data = make_api_request(f"/catalog/dataset/keyword/{keyword}", params)
                display_dataset_results(data)

        elif dataset_operation == "Buscar por ubicación":
            col1, col2 = st.columns(2)
            with col1:
                spatial_word1 = st.text_input("Palabra espacial 1", help="Ej: Autonomia")
            with col2:
                spatial_word2 = st.text_input("Palabra espacial 2", help="Ej: Madrid")
            if spatial_word1 and spatial_word2 and st.button("Buscar", type="primary"):
                data = make_api_request(f"/catalog/dataset/spatial/{spatial_word1}/{spatial_word2}", params)
                display_dataset_results(data)

        elif dataset_operation == "Buscar por fecha de modificación":
            col1, col2 = st.columns(2)
            with col1:
                begin_date = st.date_input("Fecha inicial", help="Fecha desde la que buscar")
            with col2:
                end_date = st.date_input("Fecha final", help="Fecha hasta la que buscar")
            if st.button("Buscar", type="primary"):
                begin_str = begin_date.strftime("%Y-%m-%dT00:00Z")
                end_str = end_date.strftime("%Y-%m-%dT23:59Z")
                endpoint = f"/catalog/dataset/modified/begin/{begin_str}/end/{end_str}"
                data = make_api_request(endpoint, params)
                display_dataset_results(data)

        elif dataset_operation == "Lista completa":
            if st.button("Buscar", type="primary"):
                data = make_api_request("/catalog/dataset", params)
                display_dataset_results(data)

if __name__ == "__main__":
    main()
