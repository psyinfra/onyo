#!/usr/bin/env bash

# create default folders to prepare the onyo-repo.
mkdir shelf/
mkdir user/
mkdir user2/

#onyo
onyo init .

onyo new shelf <<EOF
laptop
apple
macbookpro
867
EOF

onyo new shelf <<EOF
laptop
apple
macbookpro
2345
EOF

onyo new shelf <<EOF
laptop
apple
macbookpro
99999999
EOF

git add shelf
git add user
git add user2
#onyo tree .

onyo mv shelf/laptop_apple_macbookpro.2345 user/
onyo mv --rename shelf/laptop_apple_macbookpro.99999999 user/laptop_apple_macbookpro.88888
onyo mv --rename --force shelf/laptop_apple_macbookpro.867 user/laptop_apple_macbookpro.88888
#onyo tree

onyo mv user/* user2/
#onyo tree

onyo edit user2/laptop_apple_macbookpro.88888

onyo tree
