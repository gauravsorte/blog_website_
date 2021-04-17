from flask import Flask, render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_mail import Mail
import json
import math
import os
from werkzeug.utils import secure_filename

with open("config.json", "r") as c:
    params = json.load(c)["params"]

local_server = True

app = Flask(__name__)

app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params['gmail-user'],
    MAIL_PASSWORD=params['gmail-password']
)
mail = Mail(app)
if (local_server):
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']
#   'mysql://root:root@localhost/blogwebsite'

db = SQLAlchemy(app)
app.config['UPLOAD_FOLDER'] = params['upload_folder']

app.secret_key = 'my_super_secret_key'


class Contacts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(30), nullable=False)
    phoneno = db.Column(db.String(12), nullable=False)
    date = db.Column(db.String(12))


class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(80), nullable=False)
    slug = db.Column(db.String(80), nullable=False)
    content = db.Column(db.String(1000), nullable=False)
    date = db.Column(db.String(12), nullable=False)
    img_file = db.Column(db.String(45), nullable=True)


@app.route("/")
def home_page():
    posts = Posts.query.filter_by().all()

    last = math.ceil(len(posts)/int(params['no_of_posts']))
    pagination = [i for i in range(1, last+1)]
    page = request.args.get('page')
    if(not str(page).isnumeric()):
        page=1
    page=int(page)
    posts=posts[(page-1)*int(params['no_of_posts']): (page-1)*int(params['no_of_posts']) + int(params['no_of_posts'])]
    if page==1:
        prev='/#'
        next='/?page='+str(page+1)
    elif page==last:
        prev='/?page='+str(page-1)
        next='/#'
    else:
        prev='/?page='+str(page-1)
        next='/?page='+str(page+1)

    # for i in range(1,last+1):
    #     pagination[i] = i
    return render_template('blog-standard.html', posts=posts, prev=prev, next=next, pagination=pagination, page=page)


@app.route("/about")
def about_page():
    return render_template('about.html')


@app.route("/contact", methods=['GET', 'POST'])
def contact_page():
    if (request.method == 'POST'):
        '''Add Entry to database'''
        name = request.form.get('name')
        email = request.form.get('email')
        phoneno = request.form.get('phone')
        message = request.form.get('message')

        entry = Contacts(name=name, email=email, phoneno=phoneno, msg=message, date=datetime.now())
        db.session.add(entry)
        db.session.commit()
        mail.send_message('New Message from ' + name,
                          sender=email,
                          recipients=[params['gmail-user']],
                          body=message + "\n" + phoneno
                          )

    return render_template('contact.html')


@app.route("/post/<string:post_slug>", methods=['GET', 'POST'])
def post(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()
    # print('>>>>>>>>>>>>>', post)
    return render_template('blog-single.html', params=params, post=post)


@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    if 'user' in session and session['user'] == params['admin-user']:
        posts = Posts.query.all()
        return render_template('admin_dashboard.html', params=params, posts=posts, success=None, error=None)

    if (request.method == 'POST'):
        useremail = request.form.get('useremail')
        userpassword = request.form.get('userpass')
        if useremail == params['admin-user'] and userpassword == params['admin-password']:
            session['user'] = useremail
            posts = Posts.query.all()
            return render_template('admin_dashboard.html', params=params, posts=posts, success=None, error=None)
        else:
            return render_template('signin.html')

    else:
        return render_template('signin.html')


@app.route("/edit/<string:sno>", methods=['GET', 'POST'])
def edit(sno):
    if 'user' in session and session['user'] == params['admin-user']:
        if request.method == 'POST':
            box_title = request.form.get('title')
            box_slug = request.form.get('slug')
            box_imgFile = request.form.get('img_file')
            box_content = request.form.get('content')
            print('>>>>>>>>>>>>>>s', (sno))
            if sno <= '0':
                post = Posts(title=box_title, slug=box_slug, content=box_content, img_file=box_imgFile,
                             date=datetime.now())
                db.session.add(post)
                db.session.commit()
                print('>>>>>>>>>>>>> Success')
                # posts = Posts.query.all()
                return redirect('/dashboard')
            else:
                print('>>>>>>>>>>>>>>>>>> inside else', sno == '0', '>>>>> ', sno, '>>>>> ', type(sno))
                print(sno == '1')
                post = Posts.query.filter_by(sno=sno).first()
                post.title = box_title
                post.slug = box_slug
                post.content = box_content
                post.img_file = box_imgFile
                post.date = datetime.now()
                db.session.commit()
                redirect('/edit/' + sno)
        post = Posts.query.filter_by(sno=sno).first()
        return render_template('edit.html', params=params, post=post)
    else:
        return render_template('signin.html')

@app.route("/uploader", methods=['GET', 'POST'])
def uploader():
    if "user" in session and session['user']==params['admin-user'] :
        if(request.method=='POST'):
            try:
                f = request.files['file1']
                f.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(f.filename)))
                print('>>>>>>>>>>>>>>>>>> File Upload Success ')
                posts = Posts.query.all()
                success='success'
                return render_template('admin_dashboard.html', params=params, posts=posts, success=success, error=None)
            except:
                posts = Posts.query.all()
                error='error'
                return render_template('admin_dashboard.html', params=params, posts=posts, error=error, success=None)


@app.route('/logout')
def logout():
    session.pop('user')
    return redirect('/dashboard')


@app.route("/delete/<string:sno>", methods=['GET', 'POST'])
def delete(sno):
    if 'user' in session and session['user'] == params['admin-user']:
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
        return redirect('/dashboard')

@app.route('/nextPost/<string:slug>',  methods=['GET', 'POST'])
def next_post(slug):
    posts = Posts.query.all()
    try:
        for i in range(len(posts)):
            if posts[i].slug == slug:
                print('>>>>>>>',posts[i].slug )
                break
    except:
        return redirect('/post/' + posts[0].slug)
    if i+1 < len(posts):
        return redirect('/post/'+posts[i+1].slug)
    else:
        return redirect('/post/' + posts[0].slug)

@app.route('/prevPost/<string:slug>',  methods=['GET', 'POST'])
def prev_post(slug):
    posts = Posts.query.all()
    try:
        for i in range(len(posts)):
            if posts[i].slug == slug:
                break
    except:
        return redirect('/post/' + posts[len(posts) - 1].slug)

    return redirect('/post/' + posts[i - 1].slug)


app.run(debug=True)
