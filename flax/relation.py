import weakref

import flax.event as event


class WeakProperty:
    """Descriptor that automatically holds onto whatever it contains as a weak
    reference.  Reading this attribute will never raise `AttributeError`; if
    the reference is broken or missing, you'll just get `None`.

    The actual weak reference is stored in the object's `__dict__` under the
    given name, so this acts as sort of a transparent proxy that lets you
    forget you're dealing with weakrefs at all.

    Of course, if you try to assign a value that can't be weak referenced,
    you'll get a `TypeError`.  So don't do that.

    Example:

        class Foo:
            bar = WeakProperty('bar')

        obj = object()
        foo = Foo()
        foo.bar = obj
        print(foo.bar)  # <object object at ...>
        assert foo.bar is obj
        del obj
        print(foo.bar)  # None

    Note that due to the `__dict__` twiddling, this descriptor will never
    trigger `__getattr__`, `__setattr__`, or `__delattr__`.
    """
    def __init__(self, name):
        self.name = name

    def __get__(desc, self, cls):
        if self is None:
            return desc

        try:
            ref = self.__dict__[desc.name]
        except KeyError:
            return None
        else:
            value = ref()
            if value is None:
                # No sense leaving a dangling weakref around
                del self.__dict__[desc.name]
            return value

    def __set__(desc, self, value):
        self.__dict__[desc.name] = weakref.ref(value)

    def __delete__(desc, self):
        del self.__dict__[desc.name]


# TODO other thoughts:
# - only equipment can be worn
# - only creatures can wear equipment
# - equipment can only be worn by one creature at a time
# is this stuff worth putting in the relation
class Relation:
    """Some kind of relationship that exists between two entities.  Common
    example is containment: if an item is in the player's inventory, then the
    player contains the item, and a relation `Contains(player, item)` exists.
    """

    from_entity = WeakProperty('from_entity')
    to_entity = WeakProperty('to_entity')

    def __init__(self, from_entity, to_entity):
        # TODO need to break this relation somehow if one side or the other is
        # destroyed -- or maybe that's the responsibility of Entity, and this
        # should yell instead?
        self.from_entity = from_entity
        self.to_entity = to_entity

        self.attach()

    @classmethod
    def create(cls, from_entity, to_entity):
        relation = cls(from_entity, to_entity)
        return CreateRelationEvent(relation)

    def attach(self):
        self.from_entity.attach_relation(self)
        self.to_entity.attach_relation(self)

    def destroy(self):
        return self.detach()
        return DestroyRelationEvent(self)

    def detach(self):
        self.from_entity.detach_relation(self)
        self.to_entity.detach_relation(self)

        del self.from_entity
        del self.to_entity


# TODO is this a weird way to re-add "default" behavior, i don't know
class CreateRelationEvent:
    def __init__(self, relation):
        self.relation = relation
        self.target = relation.to_entity

    def fire(self, world):
        subevent = self.relation.on_create(
            self.relation.from_entity,
            self.relation.to_entity,
        )
        subevent.fire(world)
        if not subevent.cancelled:
            self.relation.attach()


class DestroyRelationEvent:
    def __init__(self, relation):
        self.relation = relation
        self.target = relation.to_entity

    def fire(self, world):
        subevent = self.relation.on_destroy(
            self.relation.from_entity,
            self.relation.to_entity,
        )
        subevent.fire(world)
        if not subevent.cancelled:
            self.relation.detach()


class Wears(Relation):
    on_destroy = event.Unequip

    # TODO finish me!!

"""
class Contains:
    on_create = event.Take
    on_destroy = event.Drop
"""
