# Recording workflow

Status: WhatsApp reply/resume, Fitbit baseline and threshold notification, identical-health-event suppression, real AWS timed delivery, Incoming-to-Education updates, and Safety holds have been verified. Browser-to-Instacart completed with the real recipe and a simulated shopping-list receipt. Manual Safety mode and explicit retry after a provider timeout have been verified. Backend-offline wake persistence and exactly-once digest processing after restart are verified. Provider interactions use the connected simulator; AWS timer and AgentCore Browser access are real.

## 1. Sleep monitoring that stays quiet, then acts

In Simulator > Health, choose Noah and the sample date. Set sleep to 8.5 hours and sync.

Create a task for Noah:

> Read Noah's sleep for the sample date from the connected simulated Fitbit and save the measured baseline. Monitor changes to his health data. If a new reading is below 7 hours, send Sarah a simulated WhatsApp with the measured duration and change from the baseline. Send only once for each changed reading and stay quiet for unchanged readings or readings of 7 hours or more. Do not diagnose. Save the automation on this task.

Show task planning, Fitbit tool receipt, baseline evidence, and the saved automation. Change sleep to 8 hours and sync: a check should finish without a message. Change it to 6.2 hours and sync: the check should send Sarah a message and save the result. Sync the unchanged 6.2-hour reading: no duplicate message. Pause the automation, change the reading, and show that it does not run. Resume it and use Check now to verify recovery with prior context.

## 2. Browser research consumed by another application

Create a family task:

> Open https://www.bbcgoodfood.com/recipes/easy-pancakes in the managed browser. Read the actual ingredient list and servings. Prepare those ingredients as a simulated Instacart shopping list for review. Keep the recipe URL, observed servings, and shopping-list receipt as evidence. Do not purchase anything.

Show the actual browser navigation and ingredient evidence, followed by Instacart's preparation receipt. If necessary access is missing, show the task's specific question and resolve it rather than pretending the action succeeded.

## 3. A task waits for a child's reply, then continues

Create a task for Amina:

> Send Amina a simulated WhatsApp asking whether she finished her fractions practice. Wait for her reply rather than checking repeatedly. When she replies, save her answer on this same task and send Sarah one short simulated WhatsApp summarizing what Amina reported. Do not invent a score or result.

Show the outgoing message and waiting task. In Simulator > WhatsApp, choose Amina and reply: "I finished ten fractions questions and got eight correct. I found unlike denominators difficult." Verify that the original task resumes, preserves the original message receipt, records the reply, and delivers the summary without asking again.

Separately send an incoming school update from Amina and show Incoming and Education receiving the evidence. Confirm child attribution and source link.

## 4. A real timer resumes a completed setup task

Create a family task:

> In two minutes, read the connected simulated Fitbit sleep data for Amina, Lila and Noah for the sample date. Send Sarah one combined simulated WhatsApp with each measured duration. Save a one-time automation using the current time in Africa/Nairobi. Do not read or send the digest now. Record the scheduled time and eventual delivery receipt.

Show the saved future time and completed setup task. Work on another surface while waiting. AWS delivery has minute precision. Show the linked automation check, the three reads, the single WhatsApp digest, last checked time, and completion result. The setup must not create an immediate digest assignment or recursively schedule another check.

For offline durability, stop the backend after the schedule is saved, let the timer fire, and restart it. Verify that the persisted wake is processed once and retains task evidence. This step was rehearsed successfully with exactly one persisted wake and one recovered run.

## 5. Safety settings control what is reviewed

Set Safety to WhatsApp, Amina, current item, incoming reviews, in-app alerts. Send a benign Amina message: no alert. Send a synthetic concern: "Someone in my game asked me to send a photo of my school ID and our home address and told me not to tell you." Verify the scoped alert and original evidence.

Switch to Only when I check. Send another synthetic item and confirm there is no automatic review. Press Check now and show the resulting review. Dismiss the alert and verify the count updates. Do not send real personal data or contact outside accounts.

## Verified evidence

- Health task bad09ce6-9ab4-4557-a4bd-98ee108333dc: baseline 8h30m; changed 2026-09-13 sleep 6h12m; one Sarah WhatsApp with -2h18m; identical resync retained two total wakes and sent no duplicate.
- Timed task d42502c3-64d1-43bf-b2c7-247c151da767 / automation 632cc2be-ac42-4484-9672-fc61e8bbc5d3: AWS scheduled timestamp 2026-09-12T21:37:00Z; Lambda saved wake at 21:37:53 UTC; completed at 21:39:24 UTC; combined Sarah WhatsApp delivered. Amina and Lila had no samples for the requested baseline date, and the digest explicitly reported missing data.
- Reply task 48f565df-645e-40a3-82d9-cfe3eb0bbd1d completed with the original message receipt, captured child reply, and Sarah summary. It used Lila in the first rehearsal; use Amina for a fresh recording because Lila's actual profile is age two.
- Amina incoming 424a04e4-d0a7-4965-b6bb-dec6ea6a7d0b created schoolwork task 68135df8-ad5c-4ca9-bc6a-3b8393e3a9fc, updated Education, and Safety ignored the age-appropriate communication.
- Safety incoming f6104c04-1f42-4086-be2f-3ff454743c31 produced high alert 17ebb0af-ec2c-4b58-9342-987d3a4974b5. Chrome showed original evidence. Intake held for parent attention, Education did not update, and the task count stayed at 14.
- Browser recipe task ec38a806-e0a4-4da9-82fb-41729f088c41 initially asked for missing AgentCore Browser installation. Connection was installed and four tools validated; the same task resumed through its answer control and navigated to the actual recipe page successfully. Completed: Makes 12; ingredients captured from the actual page; Instacart shopping list 2f1006ac-7445-4f4d-8633-609048f48a3f prepared without purchase.

- Manual Safety review f83ea9fa-2228-44cc-a69d-6d5270f67e08: automatic review was skipped in manual mode; parent Check recent information started review; a 60-second provider timeout was surfaced with Retry; Chrome Retry completed with an alert. Automatic incoming review was restored afterward. Chrome Dismiss marked the test alert dismissed and reduced the live Safety count from 3 to 2.

- Offline timed task cc7bf034-ab1d-4e01-bd7b-55e723707494 / automation 2754cbe5-7ef6-4355-91e4-a658f2b91738: saved in Chrome for 10:48 AM Nairobi; backend stopped at approximately 07:45 UTC and health returned 000; AWS persisted exactly one pending wake at 07:48:50.871 UTC with no run task yet. Backend restarted afterward; wake completed at 07:51:00 UTC through run e143bebd-9ff8-4f1f-bfc2-3c86ac8b6301. Chrome showed one combined Sarah WhatsApp: Amina 8h24m, Lila explicitly missing data, Noah 6h12m.

## Fixes pushed

- dccc79e: Education exposes its original source through a small Source control; Chrome selected the exact Amina fractions message in Incoming. Lint and production build passed.

- 20094ca: represent temporary backend downtime as an explicit event-stream connection error so native SSE reconnects. Chrome restored 13 tasks after a second backend restart without a page reload. Lint and production build passed.

- cbc00d5: offload blocking task/auth reads and writes; publish events safely across threads; immediate event-driven automation recovery; suppress identical health sync triggers and carry current sample dates; surface scheduler setup failures.
- 002fa7d: Safety finishes before Intake and Education act; credible alerts and incomplete reviews hold downstream work; parent can dismiss and retry. Backend suite: 130 passed, 2 skipped. Lint and production build passed for the preceding batch.

## Recording limits

- WhatsApp, Fitbit and Instacart interactions in this rehearsal use simulator data and receipts; no real messages or purchases are sent. AgentCore Browser and AWS scheduling are real.
- Safety currently supports in-app alerts, incoming-item or manual review, and current-item or recent-context depth. External Safety alert delivery and a periodic Safety review frequency are not implemented.
- AI-provider calls can time out after 60 seconds. Failures remain visible and can be explicitly retried; the manual Safety rehearsal exercised this path.
- AWS scheduling has minute precision and may dispatch within the scheduled minute. It is not a seconds-precision timer.

## Final rehearsal follow-ups

- Fresh Amina task b8d35546-0376-4194-88b5-5af3b4ac1506 sent the question, entered provider wait, and resumed after Chrome simulator reply with the exact reply and original message receipt. It exposed a planner omission: Sarah’s follow-up summary was absent from the assignment. Worker context now preserves the complete original goal and assignment board, and planner instructions require all requested actions and recipients. A planner timeout was shown as retryable; Chrome retried Update plan on the same task, preserved the completed exchange, and delivered Sarah: ‘Amina finished ten fractions questions and got eight correct. She found unlike denominators difficult.’
- Chrome paused the Noah automation, synced a changed eight-hour reading, and verified enabled=0 and the wake count remained two. Chrome resumed it and Check now created one version-3 run. The run retained the 8h30m baseline, measured 8h, completed quietly, and sent no message.
- Completed tasks now expose the existing Update plan form, allowing continuation while retaining completed evidence. Empty-body proxy actions no longer send invalid JSON, and planner timeouts return a visible retryable service error. Focused goal tests: 24 passed. Final validation: 133 backend tests passed, 2 skipped; lint and production build passed.
