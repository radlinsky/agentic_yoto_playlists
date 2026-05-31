# Deriving a 16x16 icon keyword from a track title

Icon search is in **English**; most of this user's titles are French. Rule:

1. Lowercase the title.
2. Strip ordering prefixes: `S1E1_`, leading track numbers, `1/4`, `2_4`, etc.
3. Cut everything from the first comma or the word `avec` (French credits list
   the hosts after `avec` -- ignore them).
4. Take the first **concrete noun** (the subject/object the episode is about).
5. Translate it to ONE English noun -> that is the icon search tag.
6. Search the Yoto icon library for that tag; if nothing fits, try a synonym,
   then `fetch_icon.py`, then `gen_icon.py`.

## Mapping for the 3 existing playlists (defaults; pick best available)

### Contes musicaux de Passe Partout
| Track | Keyword | Fallback letter |
|-------|---------|-----------------|
| Sékou et le voleur de coquillage | seashell / shell | S |
| Le royaume des Baladoux | castle / crown | B |
| Louna et le hibou somnambule | owl | L |
| Tarek et la marchande de bonheur | heart | T |
| Crapaudine, l'attrapeuse de cauchemars | frog / toad (or moon) | C |
| Philomène et le petit bateau en papier | boat | P |

### Le Long de la rivière
| Track | Keyword | Fallback letter |
|-------|---------|-----------------|
| 1/4 La source | water drop / spring | 1 |
| 2/4 Le radeau | raft (or boat) | 2 |
| 3/4 Le camping sauvage | tent / campfire | 3 |
| 4/4 La mer | wave / sea | 4 |

### Les zinstrus (musical instruments)
| Track | Keyword | Fallback letter |
|-------|---------|-----------------|
| Découvrez les Zinstrus (intro) | microphone / music note | Z |
| L'accordéon | accordion | A |
| L'harmonica | harmonica (or mouth organ) | H |
| L'orgue | organ (pipe organ) | O |
| La clarinette | clarinet | C |
| La flûte à bec | recorder / flute | F |
| La guitare | guitar | G |
| La harpe | harp | H |
| La trompette | trumpet | T |
| La voix | singing / microphone | V |
| Le clavecin | harpsichord (or piano) | C |
| Le piano | piano | P |
| Le saxophone | saxophone | S |
| Le ukulélé | ukulele | U |
| Les percussions | drum | P |
| Retrouvez tous les épisodes (outro) | music note | R |

Yoto's library is music-focused, so most instruments should have a real icon.
Rarer ones (harmonica, harpsichord, recorder) may fall back to a near synonym or
a generated letter icon.
