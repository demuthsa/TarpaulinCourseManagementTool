from flask import Flask, request, jsonify, send_file, render_template
from google.cloud import datastore, storage
import io
import requests
import json
from six.moves.urllib.request import urlopen
from jose import jwt
from authlib.integrations.flask_client import OAuth

PHOTO_BUCKET='a6_demuthsa'

app = Flask(__name__)
app.secret_key = 'SECRET_KEY'
app.config['TEMPLATES_AUTO_RELOAD'] = True  # This line ensures templates are auto-reloaded
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # This line ensures static files are not cached

client = datastore.Client(project='a6-course-management-tool')

USERS = "users"
COURSES = 'courses'

ERROR_BAD_REQUEST = {"Error": "The request body is invalid"}
ERROR_UNAUTHORIZED = {"Error": "Unauthorized"}
ERROR_FORBIDDEN = {"Error": "You don't have permission on this resource"}
ERROR_NOT_FOUND = {"Error": "Not found"}
ERROR_INVALID = {"Error": "Enrollment data is invalid"}

# Update the values of the following 3 variables
CLIENT_ID = 'pFH4VFGy8aeTsxBNPGOQhu8Ks5ppqrUN'
CLIENT_SECRET = 'cHpaC2abb8ezK28JGxVnD-FZjVo0mvWxVOhD_TdqZB7XQJCEbdtirqOCz5DBE399'
DOMAIN = 'a5-jwt.us.auth0.com'

ALGORITHMS = ["RS256"]

oauth = OAuth(app)

auth0 = oauth.register(
    'auth0',
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    api_base_url="https://" + DOMAIN,
    access_token_url="https://" + DOMAIN + "/oauth/token",
    authorize_url="https://" + DOMAIN + "/authorize",
    client_kwargs={
        'scope': 'openid profile email',
    },
)

class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code

@app.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response

def verify_jwt(request):
    if 'Authorization' in request.headers:
        auth_header = request.headers['Authorization'].split()
        token = auth_header[1]
    else:
        raise AuthError({"code": "no auth header",
                            "description":
                                "Authorization header is missing"}, 401)
    
    jsonurl = urlopen("https://"+ DOMAIN+"/.well-known/jwks.json")
    jwks = json.loads(jsonurl.read())
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.JWTError:
        return None

    if unverified_header["alg"] == "HS256":
        return None

    rsa_key = {}
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }
    if rsa_key:
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=ALGORITHMS,
                audience=CLIENT_ID,
                issuer="https://"+ DOMAIN+"/"
            )
        except jwt.ExpiredSignatureError:
            raise AuthError({"code": "token_expired",
                            "description": "token is expired"}, 401)
        except jwt.JWTClaimsError:
            raise AuthError({"code": "invalid_claims",
                            "description":
                                "incorrect claims,"
                                " please check the audience and issuer"}, 401)
        except Exception:
            raise AuthError({"code": "invalid_header",
                            "description":
                                "Unable to parse authentication"
                                " token."}, 401)

        return payload
    else:
        raise AuthError({"code": "no_rsa_key",
                            "description":
                                "No RSA key in JWKS"}, 401)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/decode', methods=['GET'])
def decode_jwt():
    payload = verify_jwt(request)
    return payload

@app.route('/users/login', methods=['POST'])
def login_user():
    content = request.get_json()
    if 'username' not in content or 'password' not in content:
        return ERROR_BAD_REQUEST, 400

    username = content["username"]
    password = content["password"]
    body = {'grant_type':'password',
            'username':username,
            'password':password,
            'client_id':CLIENT_ID,
            'client_secret':CLIENT_SECRET
           }
    headers = { 'content-type': 'application/json' }
    url = 'https://' + DOMAIN + '/oauth/token'
    r = requests.post(url, json=body, headers=headers)

    if r.status_code != 200:
        return ERROR_UNAUTHORIZED, 401

    token = r.json()
    
    return {
        'token': token.get('id_token')
    }, 200, {'Content-Type':'application/json'}

@app.route('/users', methods=['GET'])
def get_users():
    payload = verify_jwt(request)
    if payload is None:
        return ERROR_UNAUTHORIZED, 401

    if 'admin' not in payload["nickname"]:
        return ERROR_FORBIDDEN, 403
    
    query = client.query(kind=USERS)
    results = list(query.fetch())
    users =[]
    for r in results:
        user = {
            'id': r.key.id,
            'role': r.get('role'),
            'sub': r.get('sub')
        }
        users.append(user)
    return users, 200

@app.route('/users/<int:user_id>', methods=['GET'])
def get_a_user(user_id):
    payload = verify_jwt(request)
    if payload is None:
        return ERROR_UNAUTHORIZED, 401
    
    user_key = client.key(USERS, user_id)
    user = client.get(key=user_key)
    
    if payload.get('role') != 'admin' and payload['sub'] != user['sub']:
        return ERROR_FORBIDDEN, 403

    if 'student' in payload['nickname'] or 'instructor' in payload['nickname']:
        user['id'] = user_id
        course_key = client.key(COURSES, user_id)
        course = client.get(key=course_key)
        user['courses'] = []
        user['courses'].append(course)
        return user
    if 'admin' in payload['nickname']:
        user['id'] = user_id
        return user
    return user

@app.route('/users/<int:user_id>/avatar', methods=['POST'])
def update_user_avatar(user_id):
    payload = verify_jwt(request)
    user_key = client.key(USERS, user_id)
    user = client.get(key=user_key)

    if payload is None:
        return ERROR_UNAUTHORIZED, 401
    if payload['sub'] != user['sub']:
        return ERROR_FORBIDDEN, 403

    if 'file' not in request.files:
        return ERROR_BAD_REQUEST, 400
    
    file_obj = request.files['file']

    storage_client = storage.Client('a6-course-management-tool')
    bucket = storage_client.get_bucket(PHOTO_BUCKET)
    blob = bucket.blob(f'avatars/{user_id}.png')

    file_obj.seek(0)
    blob.upload_from_file(file_obj)

    avatar_url = f'{request.url_root.rstrip("/")}/users/{user_id}/avatar'

    user.update({'avatar_url': avatar_url})
    client.put(user)
   
    return jsonify({'avatar_url': avatar_url}), 200

@app.route('/users/<int:user_id>/avatar', methods=['GET'])
def get_user_avatar(user_id):
    payload = verify_jwt(request)
    user_key = client.key(USERS, user_id)
    user = client.get(key=user_key)

    if payload is None:
        return ERROR_UNAUTHORIZED, 401
    if payload['sub'] != user['sub']:
        return ERROR_FORBIDDEN, 403
    if 'avatar_url' not in user:
        return ERROR_NOT_FOUND, 404
    
    storage_client = storage.Client('a6-course-management-tool')
    bucket = storage_client.get_bucket(PHOTO_BUCKET)
    blob = bucket.blob(f'avatars/{user_id}.png')
    file_obj = io.BytesIO()
    blob.download_to_file(file_obj)
    file_obj.seek(0)
    return send_file(file_obj, mimetype='image/png', download_name=f'avatars/{user_id}.png')

@app.route('/users/<int:user_id>/avatar', methods=['DELETE'])
def delete_avatar(user_id):
    payload = verify_jwt(request)
    user_key = client.key(USERS, user_id)
    user = client.get(key=user_key)

    if payload is None:
        return ERROR_UNAUTHORIZED, 401
    if payload['sub'] != user['sub']:
        return ERROR_FORBIDDEN, 403
    
    if 'avatar_url' not in user:
        return ERROR_NOT_FOUND, 404
    
    del user['avatar_url']
    client.put(user)

    storage_client = storage.Client('a6-course-management-tool')
    bucket = storage_client.get_bucket(PHOTO_BUCKET)
    blob = bucket.blob(f'avatars/{user_id}.png')
    blob.delete()
    return '',204

@app.route('/courses', methods=['POST'])
def create_course():
    payload = verify_jwt(request)
    content = request.get_json()
    user_key = client.key(USERS, content["instructor_id"])
    user = client.get(key=user_key)
    if payload is None:
        return ERROR_UNAUTHORIZED, 401
    if 'admin' not in payload["nickname"]:
        return ERROR_FORBIDDEN, 403

    required_attributes = ["subject", "number", "title", "term", "instructor_id"]
    missing_attributes = [field for field in required_attributes if field not in content]
    if missing_attributes:
        return ERROR_BAD_REQUEST, 400
    if user.get('role') != 'instructor':
        return ERROR_BAD_REQUEST, 400
    
    new_course = datastore.entity.Entity(key=client.key(COURSES))
    client.put(new_course)
    course_id = new_course.key.id
    course_url = f'{request.url_root.rstrip("/")}/courses/{course_id}'
    new_course.update({
        "id": course_id,
        "subject": content["subject"],
        "number": content["number"],
        "title": content["title"],
        "term": content["term"],
        "instructor_id": content["instructor_id"],
        "self": course_url
    })
    client.put(new_course)
    return new_course, 201

@app.route('/courses', methods=['GET'])
def get_courses():
    offset = request.args.get('offset', default=0, type=int)
    limit = request.args.get('limit', default=3, type=int)

    query = client.query(kind=COURSES)
    query.order = ['subject']  
    courses = list(query.fetch())

    paginated_courses = courses[offset:offset + limit]

    courses_list = []
    for course in paginated_courses:
        course_data = {
            'id': course.key.id,
            'instructor_id': course['instructor_id'],
            'number': course['number'],
            'self': course['self'],
            'subject': course['subject'],
            'term': course['term'],
            'title': course['title']
        }
        courses_list.append(course_data)

    next_offset = offset + limit
    if next_offset < len(courses):
        next_url = f"{request.url_root.rstrip("/")}/courses?limit={limit}&offset={next_offset}"
    else:
        next_url = None

    response = {
        'courses': courses_list,
        'next': next_url
    }

    return response, 200

@app.route('/courses/<int:course_id>', methods=["GET"])
def get_course(course_id):
    course_key = client.key(COURSES, course_id)
    course = client.get(key=course_key)

    if course is None:
        return ERROR_NOT_FOUND, 404
    
    return course, 200

@app.route('/courses/<int:course_id>', methods=['PATCH'])
def update_course(course_id):
    payload = verify_jwt(request)

    course_key = client.key(COURSES, course_id)
    course = client.get(key=course_key)

    if payload is None:
        return ERROR_UNAUTHORIZED, 401
    
    if course is None:
        return ERROR_FORBIDDEN, 403
    
    if 'admin' not in payload['nickname']:
        return ERROR_FORBIDDEN, 403
    
    content = request.get_json()

    if "instuctor_id" in content:
        user_key = client.key(USERS, content["instructor_id"])
        user = client.get(key=user_key)
        if user.get('role') != 'instructor':
            return ERROR_BAD_REQUEST, 400
    
    attributes = ['subject', 'number', 'title', 'term', 'instructor_id']
    for attribute in attributes:
        if attribute in content:
            course[attribute] = content[attribute]
    
    client.put(course)

    course_response = {
        'id': course.key.id,
        'instructor_id': course['instructor_id'],
        'number': course['number'],
        'self': course['self'],
        'subject': course['subject'],
        'term': course['term'],
        'title': course['title']
    }

    return course_response, 200

@app.route('/courses/<int:course_id>', methods=["DELETE"])
def delete_course(course_id):
    payload = verify_jwt(request)
    course_key = client.key(COURSES, course_id)
    course = client.get(key=course_key)

    if payload is None:
        return ERROR_UNAUTHORIZED, 401
    
    if course is None:
        return ERROR_FORBIDDEN, 403
    
    if 'admin' not in payload['nickname']:
        return ERROR_FORBIDDEN, 403
    
    client.delete(course.key)
    
    return '', 204

@app.route('/courses/<int:course_id>/students', methods=['PATCH'])
def update_enrollment(course_id):
    payload = verify_jwt(request)
    course_key = client.key(COURSES, course_id)
    course = client.get(key=course_key)

    if payload is None:
        return ERROR_UNAUTHORIZED, 401
    
    if course is None:
        return ERROR_FORBIDDEN, 403
    
    user_key = client.key(USERS, course["instructor_id"])
    user = client.get(key=user_key)
    
    if 'admin' not in payload['nickname'] and user["sub"] != payload["sub"]:
        return ERROR_FORBIDDEN, 403
    
    content = request.get_json()

    add_students = content.get('add', [])
    remove_students = content.get('remove', [])

    if set(add_students) & set(remove_students):
        return ERROR_INVALID, 409
    
    for student_id in add_students + remove_students:
        student_key = client.key(USERS, student_id)
        student = client.get(key=student_key)
        if student is None or student.get('role') != 'student':
            return ERROR_INVALID, 409

    enrolled_students = course.get('students', [])
    for student_id in add_students:
        if student_id not in enrolled_students:
            enrolled_students.append(student_id)
    
    for student_id in remove_students:
        if student_id in enrolled_students:
            enrolled_students.remove(student_id)

    course['students'] = enrolled_students
    client.put(course)

    return '', 200

@app.route('/courses/<int:course_id>/students', methods=["GET"])
def get_enrollment(course_id):
    payload = verify_jwt(request)

    course_key = client.key(COURSES, course_id)
    course = client.get(key=course_key)

    if payload is None:
        return ERROR_UNAUTHORIZED, 401
    
    if course is None:
        return ERROR_FORBIDDEN, 403
    
    user_key = client.key(USERS, course["instructor_id"])
    user = client.get(key=user_key)

    if 'admin' not in payload['nickname'] and user['sub'] != payload['sub']:
        return ERROR_FORBIDDEN, 403

    enrollment = course['students']

    return enrollment, 200

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=True)
