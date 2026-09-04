import pytest
from src.agent.intent_router import IntentRouter
from src.agent.supervisor.user_entry import UserEntryAdapter

@pytest.fixture
def router():
    return IntentRouter()

@pytest.fixture
def adapter():
    return UserEntryAdapter()

def test_greeting_exact_matches(router):
    for q in ['hi', 'Hi', 'hi ', 'hi!', 'hello', 'hey', 'good morning']:
        res = router.route(q)
        assert res.objective_id == 'OP07_GENERAL_INQUIRY'
        assert res.path == 'Path_A_Greeting'
        assert not res.is_ambiguous

def test_greeting_casual_elongated_variants(router):
    for q in ['hii', 'hiii', 'heyy', 'heyyy', 'helloo']:
        res = router.route(q)
        assert res.objective_id == 'OP07_GENERAL_INQUIRY'
        assert res.path == 'Path_A_Greeting'
        assert not res.is_ambiguous

def test_gratitude_and_courtesy_tokens(router):
    for q in ['thanks', 'thank you', 'thx', 'ok', 'okay', 'got it', 'cool', 'bye']:
        res = router.route(q)
        assert res.objective_id == 'OP07_GENERAL_INQUIRY'
        assert res.path == 'Path_A_Greeting'
        assert not res.is_ambiguous

def test_conceptual_esp_questions(router):
    for q in ['what is an esp', 'define esp', 'explain esp', 'tell me about esp', 'how does esp work']:
        res = router.route(q)
        assert res.objective_id == 'OP07_GENERAL_INQUIRY'
        assert not res.is_ambiguous

def test_session_context_does_not_hijack_greetings(router):
    conv_ctx = {'last_well': 'FS-031', 'last_objective': 'OP03_FAULT_DIAGNOSIS'}
    for q in ['hi', 'thanks', 'ok', 'what is an esp']:
        res = router.route(q, conversation_context=conv_ctx)
        assert res.objective_id == 'OP07_GENERAL_INQUIRY'
        assert not res.is_ambiguous

def test_diagnostic_queries_preserve_routing(router):
    res = router.route('Evaluate fault and trip status for FS-031')
    assert res.objective_id == 'OP01_CURRENT_STATUS'

    res = router.route('production decline on FS-010')
    assert res.objective_id == 'OP02_PRODUCTION_DECLINE_RCA'

    res = router.route('startup procedure for pump')
    assert res.objective_id == 'OP06_PROCEDURE_LOOKUP'

    res = router.route('increase frequency of FS-031 to 55Hz')
    assert res.objective_id == 'OP00_OPERATIONAL_CONTROL'

def test_user_entry_bypasses_specialists_for_greetings(adapter):
    adv = adapter.run(user_query='hi', asset_id='FS-031')
    assert adv.objective_id == 'OP07_GENERAL_INQUIRY'
    assert 'Agent Jane' in adv.assessment
    assert any('Bypassed Specialist' in p for p in adv.provenance)
    assert len(adv.constraints) == 0

def test_user_entry_bypasses_specialists_for_gratitude(adapter):
    adv = adapter.run(user_query='thanks', asset_id='FS-031')
    assert adv.objective_id == 'OP07_GENERAL_INQUIRY'
    assert 'welcome' in adv.assessment.lower()
    assert any('Bypassed Specialist' in p for p in adv.provenance)
