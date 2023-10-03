# This is a cashback service for crypto-traders

The project is based on Binance's feature of referral incomes .csv unloading

You see, the most popular crypto exchange (binance) has a very weak api, 
that doesn't allow you to do as many cool things as their private api does.
Even tho you can access private api features through the web interface.

This is why we need to write our projects that are half automated instead of fully automating certain things

## What's this project about?

Binance has a referral program for regular users, 
that becomes the same power or even more powerful than Binance's Brocker program with certain VIP levels.

Apart from that, this approach allows users to store their money on their exchange accounts, and not transfer money to no broker, 
as well as not to show any of your trades (which is a big point for a lot of successful traders).


## Current achievements

At this moment, this project helped to save more than 50000$ worth of commissions that could have earned binance.

It's a big deal to many traders because this project essentially saves them 25-30% of commission for nothing.

And for many, it's a difference between losing and earning money from the crypto market.


#### Technical points

This project can be scaled to as many white-label cashback services as necessary. \
They can be branded differently, but have one owner.

In-bot support option allows to storing of all support dialogues forever

The system can support .csv's up to 200 megabytes right now, but it can be easily improved
to practically no cap with changes of data upload to the DB 
(right now it stores a full .csv file in memory for the convenience of data validation)


# Set up instructions

Well, there should be docker compose, but for now, we can do it with separate containers. 
So, first of all, find yourself a server with docker installed, that would be entirely dedicated to this service. 

Then, clone the "server_scripts" folder with 
```
git clone --filter=blob:none --sparse https://github.com/Arcadiyyyyyyyy/scalable_refback.git
cd scalable_refback
git sparse-checkout add server_scripts
```

After that, create a prod.env file with the keys: 
- TG_BOT_TOKEN=your_tg_bot_token
- MONGO_URI=your_mongodb_srv
- API_LOCATION=http://0.0.0.0:8000/

Now you can run your service using `/bin/bash server_scripts/update_all.sh`

Congrats, you are all done! 

If you had any issues during the process, or need any help -- please, feel free to open issues, I will be happy to help. 
