# Stars! tools

Some simple python-based tools for stars.

I don't expect these to be directly useful for anyone, but if they are, good for you :)

Currently contains two tools:

+ [merge.py](merge.py) Downloads and merges .m files of you and your ally and creates an html index with archive. 
  Uses the m/h file merger from https://github.com/tupelo-schneck/stars  (thanks!)
  I run it in a cron job outputting to a password protected public html folder (so the new merged .m file is automatically available when a new turn is in).
+ [fuel.py](fuel.py) Calculate fuel usage and booster requirements for a given trip, including slowing down and AR decay. 

Neither of them is meant to be generally useful and a lot of stuff is hard coded. 
So, if you want to use it you probably either need to adapt some things or make them more general. 
Pull requests welcome :)for your 
