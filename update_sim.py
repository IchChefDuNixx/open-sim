import requests

def update_sim():
	# repo = 'TheSench'
	repo = 'vuzaldo' # forked version with latest fixes
	url = f'https://raw.githubusercontent.com/{repo}/SIMSpellstone/gh-pages/dist/'
	for file in 'simulator.js data.min.js'.split():
		print(f'Downloading {file} from {repo}\'s SIMSpellstone repository...')
		response = requests.get(url + file).text
		# Adjust files for headless execution with multiple CPU cores
		if 'data' in file:
			response = response[17:]
		if 'sim' in file:
			response = response[:response.index(';(function (angular)')]
			with open('sim_template.js') as f: template = f.read()
			response = template.replace('### SIMULATOR CODE HERE ###', response)
		with open(file, 'w') as f: f.write(response)
	print('Simulator files ready')

# Update simulator/data
# Only needed to pull new cards/buffs/BGEs or bug fixes
update_sim()
