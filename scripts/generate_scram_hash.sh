#!/bin/bash
# Script to generate SCRAM hash for PgBouncer userlist.txt
# Usage: ./scripts/generate_scram_hash.sh username password

if [ $# -ne 2 ]; then
  echo "Usage: $0 username password"
  exit 1
fi

USERNAME=$1
PASSWORD=$2

# Connect to PostgreSQL and get the SCRAM hash
HASH=$(docker-compose exec -T db psql -U postgres -t -c "
  DO \$\$
  DECLARE
    scram_hash text;
  BEGIN
    -- Create a temporary user with the password
    EXECUTE format('CREATE USER %I WITH PASSWORD %L', 'temp_$USERNAME', '$PASSWORD');
    
    -- Get the SCRAM hash
    SELECT 'SCRAM-SHA-256' || substr(rolpassword, 4) 
    INTO scram_hash 
    FROM pg_authid 
    WHERE rolname = 'temp_$USERNAME';
    
    -- Drop the temporary user
    EXECUTE format('DROP USER IF EXISTS %I', 'temp_$USERNAME');
    
    -- Output the hash
    RAISE NOTICE 'SCRAM hash: %', scram_hash;
  END \$\$;
" | grep -o 'SCRAM-SHA-256[^ ]*' | head -1)

if [ -z "$HASH" ]; then
  echo "Failed to generate SCRAM hash"
  exit 1
fi

# Output the userlist.txt entry
echo "\"$USERNAME\" \"$HASH\""

# Update the userlist.txt file if it exists
USERLIST_FILE="docker/pgbouncer/userlist.txt"
if [ -f "$USERLIST_FILE" ]; then
  if grep -q "^\"$USERNAME\"" "$USERLIST_FILE"; then
    # Update existing user
    sed -i '' "s|^\"$USERNAME\".*|\"$USERNAME\" \"$HASH\"|" "$USERLIST_FILE"
  else
    # Add new user
    echo "\"$USERNAME\" \"$HASH\"" >> "$USERLIST_FILE"
  fi
  echo "Updated $USERLIST_FILE with new SCRAM hash"
else
  echo "$USERLIST_FILE not found. Here's the entry to add manually:"
  echo "\"$USERNAME\" \"$HASH\""
fi
