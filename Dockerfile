FROM python:3.12-slim

# Install GNU Parallel and other dependencies
RUN apt-get update && apt-get install -y parallel

# Copy the entire project into the container
COPY . /ucc

# Set the working directory to the root of your project
WORKDIR /ucc

# Set up the virtual environment
RUN python3 -m venv /venv

# Install the required dependencies and the ucc package itself
RUN /venv/bin/pip install --no-cache-dir -r /ucc/requirements.txt
RUN /venv/bin/pip install -e . && /venv/bin/pip show ucc  

# Make sure the shell script is executable
RUN chmod +x /ucc/benchmarks/scripts/run_benchmarks.sh

# Set the default command to run your benchmark script with the virtual environment activated
CMD ["/bin/bash", "-c", "source /venv/bin/activate && cd /ucc/benchmarks/scripts && ./run_benchmarks.sh"]
