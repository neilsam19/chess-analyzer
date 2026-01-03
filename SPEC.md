# "Why did I lose" app

## Inputs

### Version 1: a PGN file

### Version 2: a Lichess/Chess.com link

## Expected Output

Basically want the user to be able to play through the game. On each move want it to display a detailed explanation of each move with an engine eval like Stockfish etc.

The app will
find turning points
identify recurring mistake patterns
explains why the position collapsed in human terms

Not engine spam, but conceptual feedback.

Example output

“In 62% of your losses, the first irreversible mistake happens between moves 18–25, often after declining central tension.
This game followed the same pattern: after 19…Be7 you lost central control and never recovered.”

That’s not something engines give cleanly.
