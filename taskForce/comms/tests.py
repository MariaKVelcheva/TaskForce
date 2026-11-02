from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from taskForce.comms.models import Conversation, Message
from taskForce.tasks.models import Task
from taskForce.units.models import Membership
from taskForce.units.services import create_personal_unit, create_unit

User = get_user_model()


class CommsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cmd = User.objects.create_user("cmd", password="x")
        cls.mate = User.objects.create_user("mate", password="x")
        cls.outsider = User.objects.create_user("outsider", password="x")
        for user in (cls.cmd, cls.mate, cls.outsider):
            create_personal_unit(user)
        cls.family = create_unit(name="Family", commander=cls.cmd)
        Membership.objects.create(unit=cls.family, user=cls.mate, role="operative")


class ConversationAccessTests(CommsTestCase):
    def test_member_opens_unit_chat(self):
        self.client.force_login(self.mate)
        response = self.client.get(reverse("unit-chat", args=[self.family.pk]))
        self.assertEqual(response.status_code, 302)

    def test_outsider_cannot_open_unit_chat(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("unit-chat", args=[self.family.pk]))
        self.assertEqual(response.status_code, 404)

    def test_personal_unit_has_no_chat(self):
        self.client.force_login(self.cmd)
        response = self.client.get(reverse("unit-chat", args=[self.cmd.personal_unit.pk]))
        self.assertEqual(response.status_code, 404)

    def test_outsider_cannot_read_a_conversation(self):
        conversation = Conversation.objects.for_unit(self.family)
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("conversation", args=[conversation.pk]))
        self.assertEqual(response.status_code, 404)

    def test_task_chat_is_reused(self):
        task = Task.objects.create(name="Plan trip", user=self.cmd, unit=self.family)
        self.assertEqual(Conversation.objects.for_task(task), Conversation.objects.for_task(task))


class MessageTests(CommsTestCase):
    def test_posting_records_the_sender(self):
        conversation = Conversation.objects.for_unit(self.family)
        self.client.force_login(self.mate)
        self.client.post(reverse("conversation", args=[conversation.pk]), {"text": "On my way"})
        message = Message.objects.get(conversation=conversation)
        self.assertEqual((message.sender, message.text), (self.mate, "On my way"))

    def test_empty_message_is_not_saved(self):
        conversation = Conversation.objects.for_unit(self.family)
        self.client.force_login(self.mate)
        self.client.post(reverse("conversation", args=[conversation.pk]), {"text": ""})
        self.assertFalse(Message.objects.exists())


class InboxTests(CommsTestCase):
    def inbox(self, user, **params):
        self.client.force_login(user)
        return list(self.client.get(reverse("inbox"), params).context["conversations"])

    def test_others_messages_are_unread_own_are_not(self):
        conversation = Conversation.objects.for_unit(self.family)
        Message.objects.create(conversation=conversation, sender=self.cmd, text="Hi")

        self.assertTrue(self.inbox(self.mate)[0].has_unread)
        self.assertFalse(self.inbox(self.cmd)[0].has_unread)

    def test_opening_a_conversation_marks_it_read(self):
        conversation = Conversation.objects.for_unit(self.family)
        Message.objects.create(conversation=conversation, sender=self.cmd, text="Hi")

        self.client.force_login(self.mate)
        self.client.get(reverse("conversation", args=[conversation.pk]))
        self.assertFalse(self.inbox(self.mate)[0].has_unread)

    def test_search_lists_each_conversation_once(self):
        conversation = Conversation.objects.for_unit(self.family)
        Message.objects.create(conversation=conversation, sender=self.cmd, text="milk please")
        Message.objects.create(conversation=conversation, sender=self.mate, text="more milk")

        results = self.inbox(self.mate, query="milk")
        self.assertEqual(results, [conversation])
        self.assertEqual(results[0].match_preview, "more milk")

    def test_inbox_hides_other_units(self):
        Conversation.objects.for_unit(self.family)
        self.assertEqual(self.inbox(self.outsider), [])