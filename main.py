from os import urandom

import boto3
from flask import Flask, render_template, request, redirect, Response, url_for, session

from filters import file_type, datetimeformat

app = Flask(__name__)
app.jinja_env.filters['datetimeformat'] = datetimeformat
app.jinja_env.filters['file_type'] = file_type
app.config['SECRET_KEY'] = urandom(20)

s3_client = boto3.client('s3')
s3_resource = boto3.resource('s3')


@app.route("/")
def main_page():
    buckets = s3_resource.buckets.all()
    bucket_list = []
    for bucket in buckets:
        bucket_list.append(bucket.name)
    return render_template('main_page.html', buckets=bucket_list)


@app.route('/files', methods=['POST', 'GET'])
def files():
    if request.method == "POST":
        bucket = request.form['bucket']
        session['bucket_name'] = bucket
    else:
        if 'bucket_name' in session:
            bucket = session['bucket_name']
        else:
            redirect("/")
    my_bucket = s3_resource.Bucket(bucket)
    summaries = my_bucket.objects.all()
    return render_template('files.html', my_bucket=my_bucket, files=summaries)


@app.route('/file_move_page')
def file_moving_page():
    buckets = s3_resource.buckets.all()
    bucket_list = []
    current_bucket = session['bucket_name']
    my_bucket = s3_resource.Bucket(current_bucket)
    summaries = my_bucket.objects.all()
    for bucket in buckets:
        bucket_list.append(bucket.name)
    return render_template('move_files.html',
                           buckets=bucket_list,
                           current_bucket=current_bucket,
                           files=summaries)


@app.route('/file_copy_page')
def file_copying_page():
    buckets = s3_resource.buckets.all()
    bucket_list = []
    current_bucket = session['bucket_name']
    my_bucket = s3_resource.Bucket(current_bucket)
    summaries = my_bucket.objects.all()
    for bucket in buckets:
        bucket_list.append(bucket.name)
    return render_template('copy_files.html',
                           buckets=bucket_list,
                           current_bucket=current_bucket,
                           files=summaries)


@app.route('/delete_folder/', methods=['POST'])
def delete_folder():
    bucket_name = request.form['bucket_name']
    folder_name = request.form['folder_name']
    x = folder_name.split("/")
    folder_name = x[-2] + '/'
    my_bucket = s3_resource.Bucket(bucket_name)
    my_bucket.objects.filter(Prefix=folder_name).delete()
    return redirect(url_for('files'))


@app.route('/rename_file', methods=['POST'])
def rename_file():
    bucket_name = request.form['bucket_name']
    current_name = request.form['file_name']
    new_name = request.form['new_name']
    copy_source = {
        'Bucket': bucket_name,
        'Key': current_name
    }
    s3_resource.meta.client.copy(copy_source, bucket_name, new_name)
    s3_client.delete_object(Bucket=bucket_name, Key=current_name)
    return redirect(url_for('files'))


@app.route('/delete_file/', methods=['POST'])
def delete_file():
    file_name = request.form['file_name']
    bucket_name = request.form['bucket_name']
    s3_client.delete_object(Bucket=bucket_name, Key=file_name)

    return redirect(url_for('files'))


@app.route('/move_file', methods=['POST'])
def move_file():
    bucket_name = session['bucket_name']
    current_name = request.form['file_name']
    second_bucket_name = request.form['to_bucket']
    new_name = request.form['new_name']
    copy_source = {
        'Bucket': bucket_name,
        'Key': current_name
    }
    s3_resource.meta.client.copy(copy_source, second_bucket_name, new_name)
    s3_client.delete_object(Bucket=bucket_name, Key=current_name)
    return redirect(url_for('files'))


@app.route('/copy_file_b2b', methods=['POST'])
def copy_file_b2b():
    bucket_name = session['bucket_name']
    current_name = request.form['file_name']
    second_bucket_name = request.form['to_bucket']
    new_name = request.form['new_name']
    copy_source = {
        'Bucket': bucket_name,
        'Key': current_name
    }
    s3_resource.meta.client.copy(copy_source, second_bucket_name, new_name)
    return redirect(url_for('files'))


@app.route('/openFileInBrowser', methods=['POST'])
def open_file_in_browser():
    bucket = request.form['bucket_name']
    filename = request.form['file_name']

    new_url = s3_client.generate_presigned_url('get_object',
                                               Params={'Bucket': bucket,
                                                       'Key': filename},
                                               ExpiresIn=2000)
    return redirect(new_url)


@app.route('/download_file', methods=['POST'])
def download_file():
    filename = request.form['file_name']
    bucket = request.form['bucket_name']

    file_obj = s3_resource.Bucket(bucket).Object(filename).get()

    return Response(
        file_obj['Body'].read(),
        mimetype='text/plain',
        headers={"Content-Disposition": "attachment;filename={}".format(filename)}
    )
