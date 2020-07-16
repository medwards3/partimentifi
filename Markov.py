'''
Code adapted from a blogpost authored by Alessandro Molina
https://medium.com/@__amol__/markov-chains-with-python-1109663f3678
'''
import numpy as np
import random

class MarkovChain(object):
	def __init__(self, transition_prob):
		"""
		Initialize the MarkovChain instance.
 
		Parameters
		----------
		transition_prob: dict
			A dict object representing the transition 
			probabilities in Markov Chain. 
			Should be of the form: 
				{'state1': {'state1': 0.1, 'state2': 0.4}, 
				 'state2': {...}}
		"""
		self.transition_prob = transition_prob
		self.states = list(transition_prob.keys())
 
	def steer_state(self, current_state, desired_state):
		# desired_state is a list of tuples, giving the position and the criteria searched for
		# eg [(0, (1, None)), (2, "None")]
		possible_states = []
		for s in self.transition_prob[current_state]:
			all_criteria = []
			for criterion in desired_state:
				if (criterion[1] == s[criterion[0]]) and (self.transition_prob[current_state][s] > 0.0):
					all_criteria.append(True)
				else:
					all_criteria.append(False)
			if all (all_criteria):
				possible_states.append(s)
		
		if possible_states:
			return random.choice(possible_states)
		else:
			return self.next_state(current_state)
		'''if self.transition_prob[current_state][desired_state] > 0:
			choice_index = self.states.index(desired_state)
			return self.states[choice_index]
		else:
			return self.next_state(current_state)
		'''

	def next_state(self, current_state):
		"""
		Returns the state of the random variable at the next time 
		instance.
 
		Parameters
		----------
		current_state: str
			The current state of the system.
		"""
		choices_amount = len(self.states)
		choice_index = np.random.choice(
			choices_amount, 
			p=[self.transition_prob[current_state][next_state] 
				for next_state in self.states]
		)
		return self.states[choice_index]
	
	def generate_states(self, current_state, no=10):
		"""
		Generates the next states of the system.
 
		Parameters
		----------
		current_state: str
			The state of the current random variable.
 
		no: int
			The number of future states to generate.
		"""
		future_states = []
		for i in range(no):
			next_state = self.next_state(current_state)
			future_states.append(next_state)
			current_state = next_state
		return future_states

# Converts a dictionary into probabilities
# takes a dictionary: keys are current_states: values are lists of future_states
def create_transition_prob (d):
	transition_prob = {}
	# Iterate over all keys in the dictionary
	for key in d:
		future_states = {}
		future_states_count = {}
		total_states = 0
		# Now iterate again, checking whether every key is in the list of future_states
		for key2 in d:
			future_states_count[key2] = 0
			for val in d[key]:
				if val == key2:
					future_states_count[key2] += 1
					total_states += 1
		for val in future_states_count:
			if total_states != 0:
				future_states[val] = future_states_count[val] / total_states
			else:
				future_states[val] = 0
		transition_prob[key] = future_states
	
	return transition_prob
