
# dcbot

A Slack app for managing CTF service channels.

## Slash commands

The following slash commands work in any channel/group/chat.

### Services

#### `/listservice`

List all services that are currently online.

#### `/workon <service name>`

Specify the name of the service you want to work on.
You will then be added to the private channel for the service.

#### `/newservice <service name>`

Once a new service is created, use this slash command to create a new private channel for the service.
The channel name will be prefixed with "defcon2019-".

### Service hosts

#### `/host <service name>`

If you are a service host and you want to host a service, use this command.
I'm not checking whether you are a service host or not, but since this command will send announcements to the game channel,

#### `/unhost`

Free me from my service host duties!
`/unhost` will remove you from the current service that you are hosting.
It will not remove you from the channel of that service.

### CTF floor management

#### `/floor`

The `/floor` command will put you on a list of players who want to be on the CTF floor in Planet Hollywood.
Giovanni decides who will be invited to the CTF floor.
Once you are invited, you will receive a message in `Slackbot` like the following:

```
You are now invited to go to the CTF floor in Planet Hollywood. Don't get lost!
```

Then you are expected to show up on the CTF floor as soon as possible.
Again, don't get lost!

#### `/leavefloor`

What to do immediately before you leave the CTF floor?
What if you expressed your intent earlier but now you don't want to go to the CTF floor anymore?
`/leavefloor` is going to rescue you! Running `/leavefloor` will mark you as "I don't care if I'm going to the CTF floor or not".
You may still receive an invite to go there though.

#### `/floorstatus`

List all players' requests of going to the CTF floor, who are currently on the CTF floor, and who just want to play the game and cannot care less about everything else.

### Administration

Only the administrators (namely, Giovanni) have access to the commands in this section.

#### `/approve`

Approve a player's request of going to the CTF floor.
In fact, you can invite _any_ players to the CTF floor regardless of their intent. 

#### `/leavefloor <user>`

Mark a user as not on the CTF floor.

## TODO List

- [ ] Register events for: ~channel creation~, channel archiving, channel unarchiving
- [ ] Bot interactions: Pinning brain dumps.
- [ ] Unit tests
- Slash commands
- [x] `/listservice`
- [x] `/workon`
- [x] `/newservice`
- [x] `/host`
- [x] `/unhost` 
- [x] `/floor`
- [x] `/floorstatus`
- [ ] `/slackers`
- [ ] `/help`.
- [x] `/approve`
- [x] `/leavefloor`
