def get_model_label(model):
    """
    Take a model class or model label and return its model label.

    >>> get_model_label(MyModel)
    "myapp.MyModel"

    >>> get_model_label("myapp.MyModel")
    "myapp.MyModel"
    """
    if isinstance(model, str):
        return model
    else:
        return "{}.{}".format(
            model._meta.app_label,
            model.__name__
        )
