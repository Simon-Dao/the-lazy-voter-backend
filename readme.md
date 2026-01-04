# The Lazy Voter Backend

## Structure

### Database Updater

This downloads all of the data from several different api servers

### Database Server

Serves routes data from the database to the frontend client

### Future addition

API Key management

Extra Security features

## App Structure

### Core

Stores the main database model that is used by all other apps

## Data Sources

### Federal Election Commision

Election data such as financing and election outcomes

### Congress.gov

Data on bills, congress members, sponsored and cosponsored legislation

### voteview.com

Data on vote bills

### Google Gemini 3

For analysis of political data

1. Download all of the bills
2. For each bill, get the data for it
