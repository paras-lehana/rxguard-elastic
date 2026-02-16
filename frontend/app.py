from flask import Flask, render_template_string, request, redirect, url_for, jsonify
import os
import requests
import json
from werkzeug.utils import secure_filename
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'pharma-safe-secret-key-2024'
app.config['UPLOAD_FOLDER'] = '../data'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directory if it doesn't exist
upload_path = os.path.abspath(app.config['UPLOAD_FOLDER'])
if not os.path.exists(upload_path):
    os.makedirs(upload_path)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def call_search_api(query, session_id="pharma-session-001"):
    """
    Real API function to call the external search API
    API Endpoint: https://medical.lehana.in/ncert/api/search
    Format: {"query": "query text", "sessionId": "session-id"}
    """
    api_url = "https://medical.lehana.in/ncert/api/search"
    
    # Prepare the request data with the exact format from new API
    request_data = {
        "query": query,
        "sessionId": session_id
    }
    
    headers = {
        'Content-Type': 'application/json'
    }
    
    print(f"\n🚀 === BACKEND: Flask → External API ===")
    print(f"🎯 External API URL: {api_url}")
    print(f"🔑 Query: '{query}'")
    print(f"📝 Session ID: '{session_id}'")
    print(f"📡 Making external API call...")
    
    try:
        # Make the API call with 2-minute timeout
        print("📡 Sending request...")
        print(f"🌐 URL: {api_url}")
        print(f"📦 Headers: {headers}")
        print(f"📝 JSON Body: {json.dumps(request_data, indent=2)}")
        
        response = requests.post(
            api_url,
            json=request_data,
            headers=headers,
            timeout=120  # 2 minutes timeout
        )
        
        print(f"✅ Response Status: {response.status_code}")
        print(f"📋 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"✅ API Response: {json.dumps(response_data, indent=2)}")
            
            # The new API returns direct JSON (not wrapped in 'text' field)
            # Just pass it through as-is
            return {
                "status": "success",
                "query": query,
                "data": response_data,  # Direct data access
                "api_response": response_data,  # Keep for backward compatibility
                "api_url": api_url,
                "processing_time": "API call completed"
            }
        else:
            print(f"❌ API Error: Status {response.status_code}")
            print(f"❌ Error Response: {response.text}")
            return {
                "status": "error",
                "error": f"API returned status {response.status_code}",
                "prompt": query,
                "api_url": api_url
            }
            
    except requests.exceptions.Timeout:
        print("⏰ API call timed out after 2 minutes")
        return {
            "status": "error",
            "error": "API request timed out after 2 minutes",
            "prompt": query,
            "api_url": api_url
        }
    except requests.exceptions.ConnectionError as e:
        print(f"🌐 Connection Error: {str(e)}")
        return {
            "status": "error",
            "error": f"Connection error: {str(e)}",
            "prompt": query,
            "api_url": api_url
        }
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "prompt": query,
            "api_url": api_url
        }

def call_document_index_api(file_path, metadata=None):
    """
    Upload and index a document using the new API
    API Endpoint: https://medical.lehana.in/ncert/api/index
    """
    api_url = "https://medical.lehana.in/ncert/api/index"
    
    if metadata is None:
        metadata = {
            "source": "CDSCO",
            "type": "pharmaceutical_document",
            "year": str(time.localtime().tm_year)
        }
    
    print(f"\n📄 === UPLOAD & INDEX API ===")
    print(f"📁 File: {os.path.basename(file_path)}")
    print(f"📊 Metadata: {metadata}")
    print(f"🎯 API URL: {api_url}")
    
    try:
        with open(file_path, 'rb') as file:
            files = {'file': (os.path.basename(file_path), file, 'application/pdf')}
            data = {'metadata': json.dumps(metadata)}
            
            response = requests.post(api_url, files=files, data=data, timeout=120)
            
            print(f"✅ Response Status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"✅ API Response: {json.dumps(response_data, indent=2)}")
                return {
                    "status": "success",
                    "response": response_data
                }
            else:
                print(f"❌ API Error: {response.status_code}")
                return {
                    "status": "error",
                    "error": f"API returned status {response.status_code}"
                }
    except Exception as e:
        print(f"❌ Upload Error: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }

# Load HTML templates
def load_template(template_name):
    """Load HTML template from file"""
    try:
        with open(template_name, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        return f"Template {template_name} not found"

@app.route('/')
def root():
    """Root route - serve the main pharma AI portal"""
    try:
        template = load_template('index.html')
        return render_template_string(template)
    except Exception as e:
        return f"Error loading index page: {str(e)}", 500

@app.route('/pharmai')
def pharmai():
    """Main pharma AI portal - same as root for Traefik compatibility"""
    try:
        template = load_template('index.html')
        return render_template_string(template)
    except Exception as e:
        return f"Error loading index page: {str(e)}", 500

@app.route('/pharmai/analyze')
@app.route('/analyze')
def analyze():
    """Analysis results page route"""
    query = request.args.get('query', '')
    analysis_type = request.args.get('type', 'search')
    
    if not query and analysis_type == 'search':
        return redirect('/')
    
    try:
        # Call API for search queries
        if analysis_type == 'search':
            api_response = call_search_api(query)
        
        template = load_template('result.html')
        return render_template_string(template)
    except Exception as e:
        return f"Error loading results page: {str(e)}", 500

@app.route('/pharmai/esportal')
@app.route('/esportal')
def esportal():
    """Redirect esportal to main page"""
    return redirect('/')

@app.route('/pharmai/upload', methods=['POST'])
@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file upload and analysis"""
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        if not files or all(file.filename == '' for file in files):
            return jsonify({'error': 'No files selected'}), 400
        
        uploaded_files = []
        
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to avoid filename conflicts
                timestamp = str(int(time.time()))
                filename = f"{timestamp}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                uploaded_files.append(file_path)
        
        if not uploaded_files:
            return jsonify({'error': 'No valid PDF files uploaded'}), 400
        
        # Call new document index API for each file
        index_results = []
        for file_path in uploaded_files:
            api_response = call_document_index_api(file_path)
            index_results.append({
                'file': os.path.basename(file_path),
                'result': api_response
            })
            # Clean up uploaded file after indexing
            try:
                os.remove(file_path)
            except OSError:
                pass
        
        # Redirect to results page with upload type
        query_param = f"Document Analysis: {len(uploaded_files)} files indexed"
        return redirect(f'/analyze?query={query_param}&type=upload')
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/pharmai/api/upload-files', methods=['POST'])
@app.route('/api/upload-files', methods=['POST'])
def api_upload_files():
    """API endpoint for file upload with status notifications"""
    try:
        if 'files' not in request.files:
            return jsonify({
                'success': False,
                'message': 'No files provided'
            }), 400
        
        files = request.files.getlist('files')
        if not files or all(file.filename == '' for file in files):
            return jsonify({
                'success': False,
                'message': 'No files selected'
            }), 400
        
        uploaded_files = []
        uploaded_file_names = []
        
        # Process each file
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                
                # Option 1: Direct file save (current implementation)
                file_path = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                file.save(file_path)
                uploaded_files.append(file_path)
                uploaded_file_names.append(filename)
                print(f"📁 File uploaded successfully: {filename} -> {file_path}")
                
                # Option 2: External API call (if you want to use an API instead)
                # upload_api_url = "http://82.112.235.26:8001/v1/pw_upload_document"
                # files_data = {'file': (filename, file.read(), 'application/pdf')}
                # response = requests.post(upload_api_url, files=files_data, timeout=60)
                # if response.status_code == 200:
                #     uploaded_files.append(filename)
                #     uploaded_file_names.append(filename)
                #     print(f"📁 File uploaded via API: {filename}")
                # else:
                #     print(f"❌ API upload failed for {filename}: {response.status_code}")
        
        if not uploaded_files:
            return jsonify({
                'success': False,
                'message': 'No valid PDF files uploaded'
            }), 400
        
        # Call new document index API for each file
        index_results = []
        for file_path in uploaded_files:
            api_response = call_document_index_api(file_path)
            index_results.append({
                'file': os.path.basename(file_path),
                'indexed': api_response.get('status') == 'success'
            })
            # Clean up uploaded file after indexing
            try:
                os.remove(file_path)
            except OSError:
                pass
        
        # Return success response
        successful = sum(1 for r in index_results if r['indexed'])
        return jsonify({
            'success': successful > 0,
            'message': f'Successfully indexed {successful}/{len(uploaded_files)} file(s)',
            'files': uploaded_file_names,
            'count': len(uploaded_files),
            'indexed': successful,
            'results': index_results
        })
        
    except Exception as e:
        print(f"❌ Upload Error: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Upload failed: {str(e)}'
        }), 500

@app.route('/pharmai/api/search', methods=['POST'])
@app.route('/api/search', methods=['POST'])
def api_search():
    """API endpoint for search queries"""
    try:
        data = request.get_json()
        # Accept both 'query' (new format) and 'prompt' (old format) for backward compatibility
        query = data.get('query') or data.get('prompt')
        session_id = data.get('sessionId', 'pharma-session-001')
        
        if not query:
            return jsonify({'error': 'No query provided'}), 400
        
        print(f"📥 Received query from frontend: {query}")
        print(f"📥 Session ID: {session_id}")
        
        response = call_search_api(query, session_id)
        
        print(f"📤 Sending response to frontend: {json.dumps(response, indent=2)}")
        return jsonify(response)
    except Exception as e:
        print(f"❌ Backend API Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/pharmai/api/analyze-documents', methods=['POST'])
@app.route('/api/analyze-documents', methods=['POST'])
def api_analyze_documents():
    """API endpoint for document analysis - REPLACE WITH YOUR REAL API"""
    try:
        if 'files' not in request.files:
            return jsonify({'error': 'No files provided'}), 400
        
        files = request.files.getlist('files')
        if not files:
            return jsonify({'error': 'No files uploaded'}), 400
        
        print(f"📄 === UPLOAD API CALL ===")
        print(f"📁 Files received: {len(files)}")
        
        # Process files similar to upload route
        file_paths = []
        for file in files:
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                timestamp = str(int(time.time()))
                filename = f"{timestamp}_{filename}"
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                file_paths.append(file_path)
        
        if not file_paths:
            return jsonify({'error': 'No valid files processed'}), 400
        
        # Call dummy upload API (REPLACE THIS)
        response = call_document_analysis_api(file_paths)
        
        # Clean up files
        for file_path in file_paths:
            try:
                os.remove(file_path)
            except OSError:
                pass
        
        return jsonify(response)
    except Exception as e:
        print(f"❌ Upload API Error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/pharmai/api/delete-document', methods=['POST', 'DELETE', 'OPTIONS'])
@app.route('/api/delete-document', methods=['POST', 'DELETE', 'OPTIONS'])
def delete_document():
    """Delete a specific document by ID"""
    
    # Handle CORS preflight request
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'CORS preflight'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'POST, DELETE')
        return response
    
    try:
        data = request.get_json()
        if not data or 'documentId' not in data:
            return jsonify({'error': 'No documentId provided'}), 400
        
        document_id = data['documentId']
        api_url = "https://medical.lehana.in/ncert/api/documents/delete"
        
        print(f"[DELETE] Deleting document: {document_id}")
        
        response = requests.post(
            api_url,
            json={'documentId': document_id},
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"[DELETE] Document deleted successfully")
            resp = jsonify(result)
            resp.headers.add('Access-Control-Allow-Origin', '*')
            return resp
        else:
            error_response = jsonify({
                'error': f'Delete API returned status {response.status_code}',
                'status': 'error'
            })
            error_response.headers.add('Access-Control-Allow-Origin', '*')
            return error_response, response.status_code
            
    except Exception as e:
        print(f"[DELETE] Error: {str(e)}")
        error_response = jsonify({'error': str(e), 'status': 'error'})
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

@app.route('/pharmai/api/delete-all-documents', methods=['DELETE', 'POST', 'OPTIONS'])
@app.route('/api/delete-all-documents', methods=['DELETE', 'POST', 'OPTIONS'])
def delete_all_documents():
    """Delete all documents"""
    
    # Handle CORS preflight request
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'CORS preflight'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'DELETE, POST')
        return response
    
    try:
        api_url = "https://medical.lehana.in/ncert/api/documents/all"
        
        print(f"[DELETE ALL] Deleting all documents")
        
        response = requests.delete(api_url, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print(f"[DELETE ALL] All documents deleted successfully")
            resp = jsonify(result)
            resp.headers.add('Access-Control-Allow-Origin', '*')
            return resp
        else:
            error_response = jsonify({
                'error': f'Delete all API returned status {response.status_code}',
                'status': 'error'
            })
            error_response.headers.add('Access-Control-Allow-Origin', '*')
            return error_response, response.status_code
            
    except Exception as e:
        print(f"[DELETE ALL] Error: {str(e)}")
        error_response = jsonify({'error': str(e), 'status': 'error'})
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

@app.route('/pharmai/api/list-documents', methods=['GET', 'POST', 'OPTIONS'])
@app.route('/api/list-documents', methods=['GET', 'POST', 'OPTIONS'])
def list_documents():
    """Fetch list of documents from the RAG database"""
    
    # Handle CORS preflight request
    if request.method == 'OPTIONS':
        response = jsonify({'message': 'CORS preflight'})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST')
        return response
    
    try:
        print(f"\n[DOCUMENTS] === FETCHING DOCUMENT LIST ===")
        print(f"[DOCUMENTS] Request method: {request.method}")
        print(f"[DOCUMENTS] Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Make API call to get document list
        api_url = "https://medical.lehana.in/ncert/api/documents"
        
        print(f"[DOCUMENTS] Calling API: {api_url}")
        
        response = requests.get(
            api_url,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"[DOCUMENTS] API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            documents_data = response.json()
            documents = documents_data.get('documents', [])
            print(f"[DOCUMENTS] Retrieved {len(documents)} documents")
            
            # Add CORS headers to response
            resp = jsonify(documents)
            resp.headers.add('Access-Control-Allow-Origin', '*')
            resp.headers.add('Access-Control-Allow-Headers', 'Content-Type')
            resp.headers.add('Access-Control-Allow-Methods', 'POST, GET')
            
            return resp
        else:
            print(f"[DOCUMENTS] API Error: {response.status_code}")
            error_response = jsonify({
                'error': f'Document API returned status {response.status_code}',
                'status': 'error'
            })
            error_response.headers.add('Access-Control-Allow-Origin', '*')
            return error_response, response.status_code
            
    except requests.exceptions.RequestException as e:
        print(f"[DOCUMENTS] Connection Error: {str(e)}")
        error_response = jsonify({
            'error': f'Failed to connect to document API: {str(e)}',
            'status': 'connection_error'
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 503
        
    except Exception as e:
        print(f"[DOCUMENTS] Unexpected Error: {str(e)}")
        error_response = jsonify({
            'error': f'Unexpected error: {str(e)}',
            'status': 'error'
        })
        error_response.headers.add('Access-Control-Allow-Origin', '*')
        return error_response, 500

@app.route('/pharmai/health')
@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'PharmaSafe API',
        'version': '1.0.0',
        'timestamp': time.time()
    })

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Endpoint not found'}), 404

@app.errorhandler(413)
def too_large(error):
    """Handle file too large errors"""
    return jsonify({'error': 'File too large. Maximum size is 16MB'}), 413

@app.errorhandler(500)
def internal_error(error):
    """Handle internal server errors"""
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("🚀 Starting PharmaSafe Server...")
    print("🌐 Access the application at: http://localhost:8002/ or http://localhost:8002/pharmai")
    print("📡 API endpoints: /api/search, /api/upload-files (with /pharmai prefix support)")
    print("❤️ Health check: /health or /pharmai/health")
    print("\n🔧 Dual routes configured for Traefik compatibility:")
    print("   • Main app: / and /pharmai")
    print("   • Analyze: /analyze and /pharmai/analyze")
    print("   • APIs: /api/* and /pharmai/api/*")
    print("\n🌐 Works with Traefik reverse proxy:")
    print("   • medical.lehana.in/pharmai → Flask /")
    print("   • medical.lehana.in/pharmai/api/search → Flask /api/search")
    print("\n🎯 Starting development server on port 8002...")
    
    app.run(debug=True, host='0.0.0.0', port=8002)
