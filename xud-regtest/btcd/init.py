import pexpect
import os
import time

child = pexpect.spawn('btcwallet --simnet --username=xu --password=xu --create')
#child.expect('Enter the private passphrase for your new wallet: ')
child.expect(': ')
child.sendline('xu')
#child.expect('Confirm passphrase: ')
child.expect(': ')
child.sendline('xu')
#child.expect('Do you want to add an additional layer of encryption for public data? (n/no/y/yes) [no]: ') 
child.expect(': ')
child.sendline()
#child.expect('Do you have an existing wallet seed you want to use? (n/no/y/yes) [no]: ')
child.expect(': ')
child.sendline()
#child.expect('Once you have stored the seed in a safe and secure location, enter "OK" to continue: ')
child.expect(': ')
child.sendline('OK')

os.system('btcd --simnet --txindex --rpcuser=xu --rpcpass=xu --nolisten &')

time.sleep(5)

os.system('btcwallet --simnet --username=xu --password=xu &')

time.sleep(5)

os.system('btcctl --simnet --rpcuser=xu --rpcpass=xu --wallet walletpassphrase "xu" 600')
os.system('btcctl --simnet --rpcuser=xu --rpcpass=xu --wallet getnewaddress > /miningaddr')
