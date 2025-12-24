FROM python:3.9.6

ENV PYTHONUNBUFFERED=1

WORKDIR /code

COPY Pipfile Pipfile.lock ./
RUN python -m pip install --upgrade pip
RUN pip install pipenv && pipenv install --dev --system --deploy

WORKDIR /the_lazy_voter_backend
COPY . .

EXPOSE 8000

# During debugging, this entry point will be overridden. For more information, please refer to https://aka.ms/vscode-docker-python-debug
CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]