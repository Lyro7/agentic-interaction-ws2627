# Delegation Boundary

| Action | Decision | Justification |
| --- | --- | --- |
| Read the appointments of a day | alone | Reading the calendar does not change any appointments. |
| Look up the weather | alone | Checking the forecast is a read-only action with no side effects. |
| Reschedule an appointment with other attendees | approval | Moving the appointment affects other people's schedules, so I want to confirm the new time first. |
| Search train connections | alone | Searching gives me options without committing me to a trip. |
| Read notes | approval | My notes may contain private information, so I want to decide which ones the agent can read. |
| Create a personal block in the calendar (e.g. travel time, no other attendees) | alone | The block only affects my calendar and is easy to remove. | 
| Book a train ticket | approval | Booking costs money, so I want to confirm the connection and price first. |
| Send a message to third parties | approval | The agent speaks on my behalf, so I want to confirm the recipients and wording before it sends the message. |
| Create a note | alone | A new note is easy to remove and can be created without reading or changing my existing notes. |
| Delete a note | approval | Deleting a note can permanently remove information, so I want to confirm which note the agent will delete. |

# Rule
The agent must ask for my approval before deleting data, involving other people, spending money, or reading my notes.

## Role-Play observations
- **Card A:** The agent checked my calendar and summarized my appointments. Asking first would have been unnecessary.

- **Card B:** The agent assumed I wanted to take the train and listed all available train connections, recommended two of them, and asked which one I wanted it to book. I appreciated being asked before booking, since the slowest train was also the cheapest and I wanted to weigh price against travel time myself.