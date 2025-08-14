#!/bin/bash

# This script sets up the standard "Digital Office" directory structure
# for the Autonomous Agentic Task-Flow System (AATFS).

echo "Creating AATFS Digital Office structure..."

mkdir -p personas
mkdir -p tasks/0_pending
mkdir -p tasks/1_assigned
mkdir -p tasks/2_in_progress
mkdir -p tasks/3_review
mkdir -p tasks/4_done
mkdir -p tasks/5_failed
mkdir -p archive/deliverables

echo "Directory structure created successfully."
